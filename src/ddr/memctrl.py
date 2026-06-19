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
        "hardlimit_block_events": 0,
    }


class MemoryControllerMSC(Component):
    def __init__(
        self,
        kernel: SimulationKernel,
        config: MemoryControllerConfig,
        settings: SettingsTable,
        on_complete: Callable[[Request], None],
        enforce_controls: bool = True,
    ) -> None:
        super().__init__(config.id)
        self.kernel = kernel
        self.config = config
        self.settings = settings
        self.on_complete = on_complete
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
        if setting.bw_max_gbps is None:
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
        if setting.bw_min_gbps is None or setting.bw_min_gbps <= 0:
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
            setting.bw_limit_mode == "softlimit"
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
        return available

    def _next_token_wait(
        self, partid: int, request: Request
    ) -> float:
        if not self.enforce_controls:
            return 0.0
        setting = self.settings.lookup(partid)
        if (
            setting.bw_limit_mode != "hardlimit"
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
            aging_bonus = int(
                age / max(1.0, self.config.aging_ns)
            )
            bmin_bonus = (
                16
                if self.enforce_controls and self._under_bmin(
                    partid, request.size_bytes
                )
                else 0
            )
            soft_over = (
                self.enforce_controls
                and setting.bw_limit_mode == "softlimit"
                and setting.bw_max_gbps is not None
                and not self._max_available(
                    partid, request.size_bytes
                )
            )
            soft_penalty = 16 if soft_over and contended else 0
            effective_priority = (
                (setting.priority if self.enforce_controls else 0)
                + min(15, aging_bonus)
                + bmin_bonus
                - soft_penalty
            )
            candidates.append(
                (
                    effective_priority,
                    -sequence,
                    partid,
                    request,
                    bmin_bonus > 0,
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
            under_bmin,
            soft_over,
        ) = max(candidates)
        sequence, _ = self._queues[partid].popleft()
        request._mc_under_bmin = under_bmin
        request._mc_soft_over = soft_over
        return sequence, request

    def _consume_tokens(self, request: Request) -> None:
        if not self.enforce_controls:
            return
        partid = request.partid
        setting = self.settings.lookup(partid)
        if setting.bw_max_gbps is not None:
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

        self._interval_busy_ns += serialization_ns
        self._interval_requests += 1
        self._interval_bytes += request.size_bytes
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
            per_partid[str(partid)] = {
                **values,
                "achieved_bandwidth_gbps": (
                    values["bytes"]
                    * 8.0
                    / max(interval_ns, 1e-9)
                ),
                "bmax_gbps": (
                    setting.bw_max_gbps
                    if self.enforce_controls
                    else None
                ),
                "bmin_gbps": (
                    setting.bw_min_gbps
                    if self.enforce_controls
                    else None
                ),
                "limit_mode": (
                    setting.bw_limit_mode
                    if self.enforce_controls
                    else "disabled"
                ),
                "priority": (
                    setting.priority
                    if self.enforce_controls
                    else 0
                ),
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
                    if self.enforce_controls
                    else None
                ),
                "bmin_gbps": (
                    setting.bw_min_gbps
                    if self.enforce_controls
                    else None
                ),
                "limit_mode": (
                    setting.bw_limit_mode
                    if self.enforce_controls
                    else "disabled"
                ),
                "priority": (
                    setting.priority
                    if self.enforce_controls
                    else 0
                ),
            }

        row = {
            "msc_id": self.component_id,
            "msc_type": "memory_controller",
            "utilization": utilization,
            "queue_occupancy": (
                self._queue_sample_sum
                / max(1, self._queue_samples)
            ),
            "bytes": self._interval_bytes,
            "requests": self._interval_requests,
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
        return row
