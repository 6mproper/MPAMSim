from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, DefaultDict, Deque, Dict, Optional, Tuple

from src.config.schema import MemoryControllerConfig
from src.mpam.settings import SettingsTable
from src.sim.component import Component
from src.sim.kernel import SimulationKernel
from src.traffic.request import Request


@dataclass
class TokenState:
    tokens: float = 0.0
    last_update_ns: float = 0.0


def _mc_counters() -> Dict[str, float]:
    return {
        "requests": 0,
        "bytes": 0,
        "throttle_delay_ns": 0.0,
        "queue_delay_ns": 0.0,
        "service_delay_ns": 0.0,
        "bmin_priority_requests": 0,
        "softlimit_requests": 0,
        "softlimit_bytes": 0,
        "softlimit_penalty_events": 0,
        "hardlimit_block_events": 0,
        "effective_qos_sum": 0,
        "effective_qos_min": 7,
        "effective_qos_max": 0,
        "qos_promoted_requests": 0,
        "qos_demoted_requests": 0,
        "qos_aging_promotions": 0,
    }


class MemoryControllerMSC(Component):
    def __init__(
        self,
        kernel: SimulationKernel,
        config: MemoryControllerConfig,
        settings: SettingsTable,
        on_complete: Callable[[Request], None],
        on_cbusy: Optional[
            Callable[[str, int, int, int], None]
        ] = None,
        enforce_controls: bool = True,
    ) -> None:
        super().__init__(config.id)
        self.kernel = kernel
        self.config = config
        self.settings = settings
        self.on_complete = on_complete
        self.on_cbusy = on_cbusy
        self.enforce_controls = enforce_controls
        self._queues: DefaultDict[
            int, Deque[Tuple[int, Request]]
        ] = defaultdict(deque)
        self._sequence = 0
        self._dispatch_pending = False
        self._max_tokens: DefaultDict[int, TokenState] = defaultdict(
            TokenState
        )
        self._min_tokens: DefaultDict[int, TokenState] = defaultdict(
            TokenState
        )
        self._interval_busy_ns = 0.0
        self._interval_requests = 0
        self._interval_bytes = 0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._interval_per_partid: DefaultDict[
            int, Dict[str, float]
        ] = defaultdict(
            _mc_counters
        )
        self._interval_per_group: DefaultDict[
            Tuple[int, int], Dict[str, float]
        ] = defaultdict(
            _mc_counters
        )
        self._cbusy_sample_bytes: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_sample_hard_blocks: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_level: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_release_samples: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_last_bw_ratio: DefaultDict[int, float] = defaultdict(float)
        self._cbusy_last_queue_ratio: DefaultDict[int, float] = defaultdict(float)
        self._cbusy_interval_peak_bw_ratio: DefaultDict[
            int, float
        ] = defaultdict(float)
        self._cbusy_interval_peak_queue_ratio: DefaultDict[
            int, float
        ] = defaultdict(float)
        self._cbusy_interval_transitions: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_interval_assertions: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_interval_active_ns: DefaultDict[int, float] = defaultdict(float)
        self.kernel.schedule(
            self.config.cbusy_sample_ns,
            self._evaluate_cbusy,
            f"cbusy-sample:{self.component_id}",
        )

    @property
    def total_bandwidth_gbps(self) -> float:
        return (
            self.config.channels
            * self.config.bandwidth_gbps_per_channel
        )

    @property
    def queue_length(self) -> int:
        return sum(len(queue) for queue in self._queues.values())

    def receive(self, request: Request) -> None:
        if self.queue_length >= self.config.queue_depth:
            retry_ns = 5.0
            request.mem_queue_delay_ns += retry_ns
            self.kernel.schedule(
                retry_ns,
                lambda: self.receive(request),
                "mc-admission-retry",
            )
            return
        request.memory_controller_id = self.component_id
        request.mem_enqueue_time_ns = self.kernel.now_ns
        self._sequence += 1
        self._queues[request.partid].append((self._sequence, request))
        self._sample_queue()
        self._schedule_dispatch(0.0)

    def _schedule_dispatch(self, delay_ns: float) -> None:
        if self._dispatch_pending:
            return
        self._dispatch_pending = True
        self.kernel.schedule(
            delay_ns,
            self._dispatch,
            "mc-dispatch",
        )

    def _refill(
        self,
        partid: int,
        rate_gbps: Optional[float],
        states: DefaultDict[int, TokenState],
    ) -> None:
        if rate_gbps is None or rate_gbps <= 0:
            return
        state = states[partid]
        elapsed = max(
            0.0, self.kernel.now_ns - state.last_update_ns
        )
        bytes_per_ns = rate_gbps / 8.0
        capacity = max(
            64.0,
            bytes_per_ns * self.config.token_bucket_window_ns,
        )
        state.tokens = min(
            capacity,
            state.tokens + elapsed * bytes_per_ns,
        )
        state.last_update_ns = self.kernel.now_ns

    def _max_available(self, partid: int, size_bytes: int) -> bool:
        setting = self.settings.lookup(partid)
        if (
            not setting.bmax_enable
            or setting.bw_max_gbps is None
        ):
            return True
        self._refill(
            partid,
            setting.bw_max_gbps,
            self._max_tokens,
        )
        return (
            self._max_tokens[partid].tokens + 1e-9 >= size_bytes
        )

    def _under_bmin(self, partid: int, size_bytes: int) -> bool:
        setting = self.settings.lookup(partid)
        if (
            not setting.bmin_enable
            or setting.bw_min_gbps is None
            or setting.bw_min_gbps <= 0
        ):
            return False
        self._refill(
            partid,
            setting.bw_min_gbps,
            self._min_tokens,
        )
        return (
            self._min_tokens[partid].tokens + 1e-9 >= size_bytes
        )

    def _eligible(self, partid: int, request: Request) -> bool:
        if not self.enforce_controls:
            return True
        setting = self.settings.lookup(partid)
        if (
            not setting.bmax_enable
            or setting.bw_limit_mode == "softlimit"
            or setting.bw_max_gbps is None
        ):
            return True
        available = self._max_available(
            partid, request.size_bytes
        )
        if not available:
            self._interval_per_partid[partid][
                "hardlimit_block_events"
            ] += 1
            self._interval_per_group[
                (partid, request.pmg)
            ]["hardlimit_block_events"] += 1
            self._cbusy_sample_hard_blocks[partid] += 1
        return available

    def _next_token_wait(
        self, partid: int, request: Request
    ) -> float:
        if not self.enforce_controls:
            return 0.0
        setting = self.settings.lookup(partid)
        if (
            not setting.bmax_enable
            or setting.bw_limit_mode != "hardlimit"
            or setting.bw_max_gbps is None
        ):
            return 0.0
        self._refill(
            partid,
            setting.bw_max_gbps,
            self._max_tokens,
        )
        missing = max(
            0.0,
            request.size_bytes
            - self._max_tokens[partid].tokens,
        )
        return missing / max(
            setting.bw_max_gbps / 8.0, 1e-12
        )

    def _select_request(self) -> Optional[Tuple[int, Request]]:
        candidates = []
        contended = self.queue_length > 1
        for partid, queue in self._queues.items():
            if not queue:
                continue
            sequence, request = queue[0]
            if not self._eligible(partid, request):
                continue
            setting = self.settings.lookup(partid)
            age = max(
                0.0,
                self.kernel.now_ns
                - request.mem_enqueue_time_ns,
            )
            aging_steps = min(
                self.config.qos_aging_max_steps,
                int(
                age / max(1.0, self.config.aging_ns)
                ),
            )
            bmin_promote = (
                self.config.bmin_qos_promote
                if (
                    self.enforce_controls
                    and setting.bmin_enable
                    and self._under_bmin(
                        partid, request.size_bytes
                    )
                )
                else 0
            )
            soft_over = (
                self.enforce_controls
                and setting.bmax_enable
                and setting.bw_limit_mode == "softlimit"
                and setting.bw_max_gbps is not None
                and not self._max_available(
                    partid, request.size_bytes
                )
            )
            soft_demote = (
                self.config.softlimit_qos_demote
                if soft_over and contended
                else 0
            )
            base_qos = (
                setting.mc_qos
                if (
                    self.enforce_controls
                    and setting.mc_qos_enable
                )
                else 0
            )
            effective_qos = max(
                0,
                min(
                    7,
                    base_qos
                    + aging_steps
                    + bmin_promote
                    - soft_demote,
                ),
            )
            candidates.append(
                (
                    effective_qos,
                    -sequence,
                    partid,
                    request,
                    base_qos,
                    aging_steps,
                    bmin_promote,
                    soft_demote,
                    soft_over,
                )
            )
        if not candidates:
            return None
        (
            _,
            _,
            partid,
            request,
            base_qos,
            aging_steps,
            bmin_promote,
            soft_demote,
            soft_over,
        ) = max(candidates)
        sequence, _ = self._queues[partid].popleft()
        request._mc_base_qos = base_qos
        request._mc_effective_qos = max(
            0,
            min(
                7,
                base_qos + aging_steps + bmin_promote - soft_demote,
            ),
        )
        request._mc_aging_steps = aging_steps
        request._mc_under_bmin = bmin_promote > 0
        request._mc_soft_demoted = soft_demote > 0
        request._mc_soft_over = soft_over
        return sequence, request

    def _consume_tokens(self, request: Request) -> None:
        if not self.enforce_controls:
            return
        partid = request.partid
        setting = self.settings.lookup(partid)
        if (
            setting.bmax_enable
            and setting.bw_max_gbps is not None
        ):
            self._refill(
                partid,
                setting.bw_max_gbps,
                self._max_tokens,
            )
            if (
                self._max_tokens[partid].tokens + 1e-9
                >= request.size_bytes
            ):
                self._max_tokens[partid].tokens = max(
                    0.0,
                    self._max_tokens[partid].tokens
                    - request.size_bytes,
                )
        if (
            setting.bw_min_gbps is not None
            and setting.bmin_enable
            and setting.bw_min_gbps > 0
        ):
            self._refill(
                partid,
                setting.bw_min_gbps,
                self._min_tokens,
            )
            if (
                self._min_tokens[partid].tokens + 1e-9
                >= request.size_bytes
            ):
                self._min_tokens[partid].tokens = max(
                    0.0,
                    self._min_tokens[partid].tokens
                    - request.size_bytes,
                )

    def _dispatch(self) -> None:
        self._dispatch_pending = False
        if self.queue_length == 0:
            return

        selected = self._select_request()
        if selected is None:
            blocked = [
                (partid, queue[0][1])
                for partid, queue in self._queues.items()
                if queue
                and self.enforce_controls
                and self.settings.lookup(
                    partid
                ).bw_limit_mode
                == "hardlimit"
                and self.settings.lookup(partid).bmax_enable
            ]
            waits = [
                self._next_token_wait(partid, request)
                for partid, request in blocked
            ]
            wait_ns = max(
                0.001,
                min(waits) if waits else 0.001,
            )
            for partid, request in blocked:
                self._interval_per_partid[partid][
                    "throttle_delay_ns"
                ] += wait_ns
                self._interval_per_group[
                    (partid, request.pmg)
                ]["throttle_delay_ns"] += wait_ns
                request.throttle_delay_ns += wait_ns
            self._schedule_dispatch(wait_ns)
            return

        _, request = selected
        self._consume_tokens(request)
        queue_delay = max(
            0.0,
            self.kernel.now_ns - request.mem_enqueue_time_ns,
        )
        serialization_ns = (
            request.size_bytes
            * 8.0
            / self.total_bandwidth_gbps
        )
        service_delay = (
            self.config.base_latency_ns + serialization_ns
        )
        request.mem_queue_delay_ns += queue_delay
        request.mem_service_delay_ns += service_delay

        counters = self._interval_per_partid[
            request.partid
        ]
        counters["requests"] += 1
        counters["bytes"] += request.size_bytes
        counters["queue_delay_ns"] += queue_delay
        counters["service_delay_ns"] += service_delay
        group_counters = self._interval_per_group[
            (request.partid, request.pmg)
        ]
        group_counters["requests"] += 1
        group_counters["bytes"] += request.size_bytes
        group_counters["queue_delay_ns"] += queue_delay
        group_counters["service_delay_ns"] += service_delay
        if getattr(request, "_mc_under_bmin", False):
            counters["bmin_priority_requests"] += 1
            group_counters["bmin_priority_requests"] += 1
        if getattr(request, "_mc_soft_over", False):
            counters["softlimit_requests"] += 1
            counters["softlimit_bytes"] += request.size_bytes
            group_counters["softlimit_requests"] += 1
            group_counters["softlimit_bytes"] += request.size_bytes
        effective_qos = int(getattr(request, "_mc_effective_qos", 0))
        aging_steps = int(getattr(request, "_mc_aging_steps", 0))
        for target in (counters, group_counters):
            target["effective_qos_sum"] += effective_qos
            target["effective_qos_min"] = min(
                target["effective_qos_min"], effective_qos
            )
            target["effective_qos_max"] = max(
                target["effective_qos_max"], effective_qos
            )
            target["qos_promoted_requests"] += int(
                getattr(request, "_mc_under_bmin", False)
            )
            target["qos_demoted_requests"] += int(
                getattr(request, "_mc_soft_demoted", False)
            )
            target["qos_aging_promotions"] += aging_steps
        if getattr(request, "_mc_soft_demoted", False):
            counters["softlimit_penalty_events"] += 1
            group_counters["softlimit_penalty_events"] += 1

        self._interval_busy_ns += serialization_ns
        self._interval_requests += 1
        self._interval_bytes += request.size_bytes
        self._cbusy_sample_bytes[request.partid] += request.size_bytes
        self._sample_queue()

        self.kernel.schedule(
            service_delay,
            lambda: self.on_complete(request),
            "mc-complete",
        )
        self._schedule_dispatch(serialization_ns)

    def _sample_queue(self) -> None:
        self._queue_sample_sum += self.queue_length
        self._queue_samples += 1

    def _cbusy_cap(self, partid: int, level: int) -> int:
        setting = self.settings.lookup(partid)
        return {
            1: setting.cbusy_l1_ostd,
            2: setting.cbusy_l2_ostd,
            3: setting.cbusy_l3_ostd,
        }.get(level, max(setting.cbusy_l1_ostd, 1))

    def _detected_cbusy_level(
        self,
        partid: int,
        bandwidth_ratio: float,
        queue_ratio: float,
        hard_blocks: int,
    ) -> int:
        setting = self.settings.lookup(partid)
        if (
            not self.enforce_controls
            or not setting.cbusy_enable
        ):
            return 0
        contended = self.queue_length > 1
        bw_thresholds = (
            self.config.cbusy_l1_bw_ratio,
            self.config.cbusy_l2_bw_ratio,
            self.config.cbusy_l3_bw_ratio,
        )
        queue_thresholds = (
            self.config.cbusy_l1_queue_ratio,
            self.config.cbusy_l2_queue_ratio,
            self.config.cbusy_l3_queue_ratio,
        )
        level = 0
        for candidate in range(1, 4):
            if (
                queue_ratio >= queue_thresholds[candidate - 1]
                or (
                    setting.bmax_enable
                    and contended
                    and bandwidth_ratio
                    >= bw_thresholds[candidate - 1]
                )
            ):
                level = candidate
        if hard_blocks > 0:
            level = max(level, 2)
        return level

    def _publish_cbusy(self, partid: int, level: int) -> None:
        if self.on_cbusy is None:
            return
        cap = self._cbusy_cap(partid, level)
        self.kernel.schedule(
            self.config.cbusy_feedback_latency_ns,
            lambda: self.on_cbusy(
                self.component_id,
                partid,
                level,
                cap,
            ),
            f"cbusy-feedback:{self.component_id}:p{partid}",
        )

    def _evaluate_cbusy(self) -> None:
        configured = {partid for partid, _ in self.settings.items()}
        partids = sorted(
            configured
            | set(self._queues)
            | set(self._cbusy_sample_bytes)
            | set(self._cbusy_level)
        )
        sample_ns = self.config.cbusy_sample_ns
        for partid in partids:
            setting = self.settings.lookup(partid)
            bandwidth = (
                self._cbusy_sample_bytes[partid]
                * 8.0
                / max(sample_ns, 1e-9)
            )
            bandwidth_ratio = (
                bandwidth / setting.bw_max_gbps
                if (
                    setting.bmax_enable
                    and setting.bw_max_gbps is not None
                    and setting.bw_max_gbps > 0
                )
                else 0.0
            )
            queue_ratio = (
                len(self._queues[partid])
                / max(1, self.config.queue_depth)
            )
            detected = self._detected_cbusy_level(
                partid,
                bandwidth_ratio,
                queue_ratio,
                self._cbusy_sample_hard_blocks[partid],
            )
            current = self._cbusy_level[partid]
            new_level = current
            if (
                not self.enforce_controls
                or not setting.cbusy_enable
            ):
                new_level = 0
                self._cbusy_release_samples[partid] = 0
            elif detected > current:
                new_level = detected
                self._cbusy_release_samples[partid] = 0
            elif detected < current:
                self._cbusy_release_samples[partid] += 1
                if (
                    self._cbusy_release_samples[partid]
                    >= self.config.cbusy_release_hold_samples
                ):
                    new_level = current - 1
                    self._cbusy_release_samples[partid] = 0
            else:
                self._cbusy_release_samples[partid] = 0

            if current > 0:
                self._cbusy_interval_active_ns[partid] += sample_ns
            self._cbusy_last_bw_ratio[partid] = bandwidth_ratio
            self._cbusy_last_queue_ratio[partid] = queue_ratio
            self._cbusy_interval_peak_bw_ratio[partid] = max(
                self._cbusy_interval_peak_bw_ratio[partid],
                bandwidth_ratio,
            )
            self._cbusy_interval_peak_queue_ratio[partid] = max(
                self._cbusy_interval_peak_queue_ratio[partid],
                queue_ratio,
            )
            if new_level != current:
                self._cbusy_level[partid] = new_level
                self._cbusy_interval_transitions[partid] += 1
                if new_level > current:
                    self._cbusy_interval_assertions[partid] += 1
                self._publish_cbusy(partid, new_level)

        self._cbusy_sample_bytes.clear()
        self._cbusy_sample_hard_blocks.clear()
        self.kernel.schedule(
            sample_ns,
            self._evaluate_cbusy,
            f"cbusy-sample:{self.component_id}",
        )

    def monitor_snapshot(self, interval_ns: float) -> Dict[str, object]:
        utilization = min(
            1.0,
            self._interval_busy_ns
            / max(interval_ns, 1e-9),
        )
        configured_partids = {
            partid for partid, _ in self.settings.items()
        }
        partids = sorted(
            configured_partids
            | set(self._interval_per_partid)
        )
        per_partid = {}
        for partid in partids:
            values = dict(
                self._interval_per_partid[partid]
            )
            setting = self.settings.lookup(partid)
            requests = int(values["requests"])
            effective_qos_avg = (
                values["effective_qos_sum"] / requests
                if requests
                else 0.0
            )
            per_partid[str(partid)] = {
                **values,
                "achieved_bandwidth_gbps": (
                    values["bytes"]
                    * 8.0
                    / max(interval_ns, 1e-9)
                ),
                "bmax_gbps": (
                    setting.bw_max_gbps
                    if (
                        self.enforce_controls
                        and setting.bmax_enable
                    )
                    else None
                ),
                "bmin_gbps": (
                    setting.bw_min_gbps
                    if (
                        self.enforce_controls
                        and setting.bmin_enable
                    )
                    else None
                ),
                "limit_mode": (
                    setting.bw_limit_mode
                    if self.enforce_controls
                    else "disabled"
                ),
                "base_qos": (
                    setting.mc_qos
                    if (
                        self.enforce_controls
                        and setting.mc_qos_enable
                    )
                    else 0
                ),
                "effective_qos_avg": effective_qos_avg,
                "effective_qos_min": (
                    values["effective_qos_min"] if requests else 0
                ),
                "effective_qos_max": (
                    values["effective_qos_max"] if requests else 0
                ),
                "configured_bmax_gbps": setting.bw_max_gbps,
                "configured_bmin_gbps": setting.bw_min_gbps,
                "configured_mc_qos": setting.mc_qos,
                "bmax_enable": self.enforce_controls and setting.bmax_enable,
                "bmin_enable": self.enforce_controls and setting.bmin_enable,
                "mc_qos_enable": (
                    self.enforce_controls and setting.mc_qos_enable
                ),
                "cbusy_enable": (
                    self.enforce_controls and setting.cbusy_enable
                ),
                "cbusy_level": self._cbusy_level[partid],
                "cbusy_bandwidth_ratio": (
                    self._cbusy_last_bw_ratio[partid]
                ),
                "cbusy_queue_ratio": (
                    self._cbusy_last_queue_ratio[partid]
                ),
                "cbusy_peak_bandwidth_ratio": (
                    self._cbusy_interval_peak_bw_ratio[partid]
                ),
                "cbusy_peak_queue_ratio": (
                    self._cbusy_interval_peak_queue_ratio[partid]
                ),
                "cbusy_transitions": (
                    self._cbusy_interval_transitions[partid]
                ),
                "cbusy_assertions": (
                    self._cbusy_interval_assertions[partid]
                ),
                "cbusy_duty": min(
                    1.0,
                    self._cbusy_interval_active_ns[partid]
                    / max(interval_ns, 1e-9),
                ),
                "cbusy_ostd_cap": self._cbusy_cap(
                    partid,
                    self._cbusy_level[partid],
                ) if self._cbusy_level[partid] > 0 else None,
                "cbusy_l1_ostd": setting.cbusy_l1_ostd,
                "cbusy_l2_ostd": setting.cbusy_l2_ostd,
                "cbusy_l3_ostd": setting.cbusy_l3_ostd,
                "monitor_enable": setting.monitor_enable,
                "enforcement_enabled": self.enforce_controls,
            }

        monitor_groups = {}
        for partid, pmg in sorted(self._interval_per_group):
            values = dict(
                self._interval_per_group[(partid, pmg)]
            )
            bandwidth = (
                values["bytes"]
                * 8.0
                / max(interval_ns, 1e-9)
            )
            setting = self.settings.lookup(partid)
            requests = int(values["requests"])
            monitor_groups[f"{partid}:{pmg}"] = {
                "partid": partid,
                "pmg": pmg,
                **values,
                "achieved_bandwidth_gbps": bandwidth,
                "controller_bandwidth_gbps": self.total_bandwidth_gbps,
                "bandwidth_utilization": min(
                    1.0,
                    bandwidth / max(self.total_bandwidth_gbps, 1e-9),
                ),
                "bmax_gbps": (
                    setting.bw_max_gbps
                    if (
                        self.enforce_controls
                        and setting.bmax_enable
                    )
                    else None
                ),
                "bmin_gbps": (
                    setting.bw_min_gbps
                    if (
                        self.enforce_controls
                        and setting.bmin_enable
                    )
                    else None
                ),
                "limit_mode": (
                    setting.bw_limit_mode
                    if self.enforce_controls
                    else "disabled"
                ),
                "base_qos": (
                    setting.mc_qos
                    if (
                        self.enforce_controls
                        and setting.mc_qos_enable
                    )
                    else 0
                ),
                "effective_qos_avg": (
                    values["effective_qos_sum"] / requests
                    if requests
                    else 0.0
                ),
                "bmax_enable": self.enforce_controls and setting.bmax_enable,
                "bmin_enable": self.enforce_controls and setting.bmin_enable,
                "mc_qos_enable": (
                    self.enforce_controls and setting.mc_qos_enable
                ),
                "cbusy_enable": (
                    self.enforce_controls and setting.cbusy_enable
                ),
                "cbusy_level": self._cbusy_level[partid],
            }

        row = {
            "msc_id": self.component_id,
            "msc_type": "memory_controller",
            "total_bandwidth_gbps": self.total_bandwidth_gbps,
            "utilization": utilization,
            "queue_occupancy": (
                self._queue_sample_sum
                / max(1, self._queue_samples)
            ),
            "bytes": self._interval_bytes,
            "requests": self._interval_requests,
            "token_bucket_window_ns": self.config.token_bucket_window_ns,
            "aging_ns": self.config.aging_ns,
            "qos_aging_max_steps": self.config.qos_aging_max_steps,
            "bmin_qos_promote": self.config.bmin_qos_promote,
            "softlimit_qos_demote": self.config.softlimit_qos_demote,
            "enforcement_enabled": self.enforce_controls,
            "per_partid": per_partid,
            "monitor_groups": monitor_groups,
        }
        self._interval_busy_ns = 0.0
        self._interval_requests = 0
        self._interval_bytes = 0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._interval_per_partid.clear()
        self._interval_per_group.clear()
        self._cbusy_interval_transitions.clear()
        self._cbusy_interval_assertions.clear()
        self._cbusy_interval_active_ns.clear()
        self._cbusy_interval_peak_bw_ratio.clear()
        self._cbusy_interval_peak_queue_ratio.clear()
        return row
