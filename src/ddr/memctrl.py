from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, DefaultDict, Dict, List, Optional, Tuple

from src.config.schema import MemoryControllerConfig
from src.mpam.settings import SettingsTable
from src.sim.component import Component
from src.sim.kernel import SimulationKernel
from src.traffic.request import Request


@dataclass
class BufferEntry:
    slot: int
    sequence: int
    request: Request
    enqueue_time_ns: float


@dataclass(frozen=True)
class ArbitrationScore:
    effective_qos: int
    raw_effective_qos: int
    base_qos: int
    bmin_delta: int
    softlimit_delta: int
    soft_over: bool
    bmin_error_ratio: float
    bmax_error_ratio: float
    qos_adjust_mode: str


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
        "raw_effective_qos_sum": 0,
        "raw_effective_qos_min": 7,
        "raw_effective_qos_max": 0,
        "effective_qos_sum": 0,
        "effective_qos_min": 7,
        "effective_qos_max": 0,
        "qos_mapping_events": 0,
        "qos_promoted_requests": 0,
        "qos_demoted_requests": 0,
        "bmin_qos_delta_sum": 0,
        "softlimit_qos_delta_sum": 0,
        "bmin_error_ratio_sum": 0.0,
        "bmax_error_ratio_sum": 0.0,
        "qos_error_weighted_requests": 0,
        "qos_aging_promotions": 0,
        "qos_saturation_events": 0,
        "candidate_evaluations": 0,
        "grants": 0,
    }


class MemoryControllerMSC(Component):
    MONITOR_COUNTER_MODULUS = 1 << 63
    QOS_8_TO_4_MAP = (0, 1, 1, 1, 2, 2, 2, 3)

    capabilities = (
        "memory_controller_service",
        "shared_request_buffer",
        "full_depth_ready_candidates",
        "same_line_write_ordering",
        "three_bit_qos",
        "optional_qos_8_to_4_map",
        "rotating_slot_scan",
        "filtered_periodic_bmin_bmax",
        "optional_partid_service_deficit",
        "four_level_cbusy",
        "per_partid_monitoring",
    )
    required_monitors = (
        "raw_filtered_bandwidth",
        "queue_occupancy",
        "effective_qos",
        "candidate_grant",
        "limit_state",
    )
    actions = (
        "admit",
        "build_ready_mask",
        "select_candidate",
        "dispatch",
        "publish_monitor_state",
        "publish_cbusy",
    )
    validation_hooks = (
        "queue_capacity",
        "qos_range",
        "bmin_bmax_order",
        "monitor_weight_sum",
    )
    incompatible_capabilities = (
        "token_bucket_bmin",
        "token_bucket_bmax",
        "per_request_timestamp_aging",
    )
    approximations = (
        "fixed shared request slots",
        "monitor-interval hard BMAX gate",
        "bandwidth-only DRAM service",
    )

    def __init__(
        self,
        kernel: SimulationKernel,
        config: MemoryControllerConfig,
        settings: SettingsTable,
        on_complete: Callable[[Request], None],
        enforce_controls: bool = True,
        on_control_event: Optional[Callable[..., None]] = None,
    ) -> None:
        super().__init__(config.id, "memory_controller")
        self.kernel = kernel
        self.config = config
        self.settings = settings
        self.on_complete = on_complete
        self.enforce_controls = enforce_controls
        self.on_control_event = on_control_event

        self._buffer: List[Optional[BufferEntry]] = [
            None
            for _ in range(config.queue_depth)
        ]
        self._sequence = 0
        self._last_grant_slot = config.queue_depth - 1
        self._dispatch_pending = False
        self._peak_queue_length = 0

        self._monitor_cumulative_bytes: DefaultDict[
            int, int
        ] = defaultdict(int)
        self._monitor_last_sample_bytes: DefaultDict[
            int, int
        ] = defaultdict(int)
        self._monitor_delta_bytes: DefaultDict[int, int] = defaultdict(int)
        self._raw_bandwidth_gbps: DefaultDict[int, float] = defaultdict(float)
        self._filtered_bandwidth_gbps: DefaultDict[int, float] = defaultdict(
            float
        )
        self._control_bandwidth_gbps: DefaultDict[int, float] = defaultdict(
            float
        )
        self._under_bmin: DefaultDict[int, bool] = defaultdict(bool)
        self._over_bmax: DefaultDict[int, bool] = defaultdict(bool)
        self._hard_block: DefaultDict[int, bool] = defaultdict(bool)
        self._monitor_updates: DefaultDict[int, int] = defaultdict(int)

        self._service_deficit: DefaultDict[int, int] = defaultdict(int)
        self._grant_seen: DefaultDict[int, bool] = defaultdict(bool)

        self._interval_busy_ns = 0.0
        self._interval_requests = 0
        self._interval_bytes = 0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._interval_per_partid: DefaultDict[
            int, Dict[str, float]
        ] = defaultdict(_mc_counters)
        self._interval_per_group: DefaultDict[
            Tuple[int, int], Dict[str, float]
        ] = defaultdict(_mc_counters)

        self._cbusy_level: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_release_samples: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_last_bw_ratio: DefaultDict[int, float] = defaultdict(float)
        self._cbusy_last_queue_ratio: DefaultDict[int, float] = defaultdict(
            float
        )
        self._cbusy_interval_peak_bw_ratio: DefaultDict[
            int, float
        ] = defaultdict(float)
        self._cbusy_interval_peak_queue_ratio: DefaultDict[
            int, float
        ] = defaultdict(float)
        self._cbusy_interval_transitions: DefaultDict[int, int] = defaultdict(
            int
        )
        self._cbusy_interval_assertions: DefaultDict[int, int] = defaultdict(
            int
        )
        self._cbusy_interval_active_ns: DefaultDict[int, float] = defaultdict(
            float
        )
        self._cbusy_sample_index = 0
        self._cbusy_sample_time_ns: Dict[int, float] = {}
        self._cbusy_monitor_sample_id: Dict[int, str] = {}
        self._cbusy_decision_id: Dict[int, str] = {}

        for partid, setting in self.settings.items():
            self._under_bmin[partid] = bool(
                enforce_controls
                and setting.bmin_enable
                and setting.bw_min_gbps is not None
                and setting.bw_min_gbps > 0
            )

        self.kernel.schedule(
            self.monitor_period_ns,
            self._publish_bandwidth_monitor,
            f"mc-monitor:{self.component_id}",
        )
        if self.config.aging_mode == "per_partid_service_deficit":
            self.kernel.schedule(
                self.aging_quantum_ns,
                self._update_service_deficit,
                f"mc-deficit:{self.component_id}",
            )
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
    def monitor_period_ns(self) -> float:
        return (
            self.config.monitor_period_cycles
            * 1000.0
            / self.config.clock_mhz
        )

    @property
    def aging_quantum_ns(self) -> float:
        return (
            self.config.aging_quantum_cycles
            * 1000.0
            / self.config.clock_mhz
        )

    @property
    def queue_length(self) -> int:
        return sum(entry is not None for entry in self._buffer)

    def _partid_buffer_count(self, partid: int) -> int:
        return sum(
            entry is not None and entry.request.partid == partid
            for entry in self._buffer
        )

    def receive(self, request: Request) -> None:
        free_slot = next(
            (
                slot
                for slot, entry in enumerate(self._buffer)
                if entry is None
            ),
            None,
        )
        if free_slot is None:
            retry_ns = max(0.001, self.monitor_period_ns / 16.0)
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
        self._buffer[free_slot] = BufferEntry(
            slot=free_slot,
            sequence=self._sequence,
            request=request,
            enqueue_time_ns=self.kernel.now_ns,
        )
        self._peak_queue_length = max(
            self._peak_queue_length,
            self.queue_length,
        )
        self._sample_queue()
        self._schedule_dispatch(0.0)

    def can_accept(self, request: Request) -> bool:
        return self.queue_length < self.config.queue_depth

    def accept(self, request: Request) -> None:
        self.receive(request)

    def _schedule_dispatch(self, delay_ns: float) -> None:
        if self._dispatch_pending:
            return
        self._dispatch_pending = True
        self.kernel.schedule(
            delay_ns,
            self._dispatch,
            f"mc-dispatch:{self.component_id}",
        )

    @staticmethod
    def _same_line(first: Request, second: Request) -> bool:
        if (
            first.line_address is not None
            and second.line_address is not None
        ):
            return first.line_address == second.line_address
        return first.address // 64 == second.address // 64

    def _ordering_blocked(self, candidate: BufferEntry) -> bool:
        request = candidate.request
        for older in self._buffer:
            if (
                older is None
                or older.sequence >= candidate.sequence
                or not self._same_line(older.request, request)
            ):
                continue
            if older.request.op == "write" or request.op == "write":
                return True
        return False

    def _ready_entries(self) -> List[BufferEntry]:
        ready: List[BufferEntry] = []
        for entry in self._buffer:
            if entry is None:
                continue
            request = entry.request
            hard = bool(
                self.enforce_controls
                and self._hard_block[request.partid]
            )
            request.mc_arbitration.hard_blocked = hard
            if hard or self._ordering_blocked(entry):
                continue
            ready.append(entry)
        return ready

    def _deficit_qos_steps(self, partid: int) -> int:
        if (
            not self.enforce_controls
            or self.config.aging_mode
            != "per_partid_service_deficit"
        ):
            return 0
        return min(
            self.config.qos_aging_max_steps,
            self._service_deficit[partid],
        )

    def _map_effective_qos(self, raw_effective_qos: int) -> int:
        if not self.config.qos_map_8_to_4_enable:
            return raw_effective_qos
        return self.QOS_8_TO_4_MAP[raw_effective_qos]

    def _qos_error_delta(self, error_ratio: float, weight: float) -> int:
        if self.config.qos_error_max_delta <= 0 or weight <= 0:
            return 0
        deadband = self.config.qos_error_deadband_percent / 100.0
        active_error = max(0.0, error_ratio - deadband)
        if active_error <= 0:
            return 0
        scaled = active_error * weight
        if self.config.qos_error_quantization == "ceil":
            delta = math.ceil(scaled)
        elif self.config.qos_error_quantization == "round":
            delta = math.floor(scaled + 0.5)
        else:
            # Hardware-style comparator LUT over the weighted error value.
            delta = 0
            for level in range(1, self.config.qos_error_max_delta + 1):
                if scaled >= level - 0.5:
                    delta = level
        return max(0, min(7, self.config.qos_error_max_delta, int(delta)))

    def _bmin_qos_delta(
        self,
        partid: int,
        target_gbps: Optional[float],
    ) -> Tuple[int, float]:
        if self.config.qos_adjust_mode == "fixed_step":
            return self.config.bmin_qos_promote, 0.0
        if target_gbps is None or target_gbps <= 0:
            return 0, 0.0
        control_bw = self._control_bandwidth_gbps[partid]
        error_ratio = max(0.0, (target_gbps - control_bw) / target_gbps)
        return (
            self._qos_error_delta(
                error_ratio,
                self.config.bmin_error_weight,
            ),
            error_ratio,
        )

    def _softlimit_qos_delta(
        self,
        partid: int,
        target_gbps: Optional[float],
    ) -> Tuple[int, float]:
        if self.config.qos_adjust_mode == "fixed_step":
            return self.config.softlimit_qos_demote, 0.0
        if target_gbps is None or target_gbps <= 0:
            return 0, 0.0
        control_bw = self._control_bandwidth_gbps[partid]
        error_ratio = max(0.0, (control_bw - target_gbps) / target_gbps)
        return (
            self._qos_error_delta(
                error_ratio,
                self.config.bmax_error_weight,
            ),
            error_ratio,
        )

    def _score_entry(
        self,
        entry: BufferEntry,
        contended: bool,
    ) -> ArbitrationScore:
        request = entry.request
        setting = self.settings.lookup(request.partid)
        base_qos = (
            setting.mc_qos
            if self.enforce_controls and setting.mc_qos_enable
            else 0
        )
        bmin_delta = 0
        bmin_error_ratio = 0.0
        if (
            self.enforce_controls
            and contended
            and setting.bmin_enable
            and self._under_bmin[request.partid]
        ):
            bmin_delta, bmin_error_ratio = self._bmin_qos_delta(
                request.partid,
                setting.bw_min_gbps,
            )
        soft_over = bool(
            self.enforce_controls
            and setting.bmax_enable
            and setting.bw_limit_mode == "softlimit"
            and self._over_bmax[request.partid]
        )
        soft_delta = 0
        bmax_error_ratio = 0.0
        if soft_over and contended:
            soft_delta, bmax_error_ratio = self._softlimit_qos_delta(
                request.partid,
                setting.bw_max_gbps,
            )
        deficit_steps = self._deficit_qos_steps(request.partid)
        unclamped = (
            base_qos
            + bmin_delta
            - soft_delta
            + deficit_steps
        )
        raw_effective_qos = max(0, min(7, unclamped))
        effective_qos = self._map_effective_qos(raw_effective_qos)
        return ArbitrationScore(
            effective_qos=effective_qos,
            raw_effective_qos=raw_effective_qos,
            base_qos=base_qos,
            bmin_delta=bmin_delta,
            softlimit_delta=soft_delta,
            soft_over=soft_over,
            bmin_error_ratio=bmin_error_ratio,
            bmax_error_ratio=bmax_error_ratio,
            qos_adjust_mode=self.config.qos_adjust_mode,
        )

    def _select_request(self) -> Optional[BufferEntry]:
        candidates = self._ready_entries()
        if not candidates:
            return None
        contended = len(
            {entry.request.partid for entry in candidates}
        ) >= 2
        scored: Dict[int, ArbitrationScore] = {}
        for entry in candidates:
            scored[entry.slot] = self._score_entry(entry, contended)
            counters = self._interval_per_partid[entry.request.partid]
            counters["candidate_evaluations"] += 1
            self._interval_per_group[
                (entry.request.partid, entry.request.pmg)
            ]["candidate_evaluations"] += 1
        highest_qos = max(
            values.effective_qos for values in scored.values()
        )
        candidate_slots = {
            slot
            for slot, values in scored.items()
            if values.effective_qos == highest_qos
        }
        selected: Optional[BufferEntry] = None
        for offset in range(1, self.config.queue_depth + 1):
            slot = (
                self._last_grant_slot + offset
            ) % self.config.queue_depth
            if slot in candidate_slots:
                selected = self._buffer[slot]
                break
        if selected is None:
            return None

        score = scored[selected.slot]
        deficit_steps = self._deficit_qos_steps(
            selected.request.partid
        )
        request = selected.request
        request.mc_arbitration.base_qos = score.base_qos
        request.mc_arbitration.raw_effective_qos = (
            score.raw_effective_qos
        )
        request.mc_arbitration.effective_qos = score.effective_qos
        request.mc_arbitration.qos_mapping_enabled = (
            self.config.qos_map_8_to_4_enable
        )
        request.mc_arbitration.aging_steps = deficit_steps
        request.mc_arbitration.qos_adjust_mode = score.qos_adjust_mode
        request.mc_arbitration.bmin_qos_delta = score.bmin_delta
        request.mc_arbitration.softlimit_qos_delta = (
            score.softlimit_delta
        )
        request.mc_arbitration.bmin_error_ratio = (
            score.bmin_error_ratio
        )
        request.mc_arbitration.bmax_error_ratio = (
            score.bmax_error_ratio
        )
        request.mc_arbitration.bmin_promoted = score.bmin_delta > 0
        request.mc_arbitration.soft_demoted = (
            score.softlimit_delta > 0
        )
        request.mc_arbitration.soft_over_limit = score.soft_over
        request.mc_arbitration.hard_blocked = False
        request.mc_arbitration.selected_sequence = selected.sequence
        self._buffer[selected.slot] = None
        self._last_grant_slot = selected.slot
        self._grant_seen[request.partid] = True
        return selected

    def _dispatch(self) -> None:
        self._dispatch_pending = False
        if self.queue_length == 0:
            return
        selected = self._select_request()
        if selected is None:
            return

        request = selected.request
        queue_delay = max(
            0.0,
            self.kernel.now_ns - selected.enqueue_time_ns,
        )
        serialization_ns = (
            request.size_bytes
            * 8.0
            / self.total_bandwidth_gbps
        )
        service_delay = self.config.base_latency_ns + serialization_ns
        request.mem_queue_delay_ns += queue_delay
        request.mem_service_delay_ns += service_delay

        counters = self._interval_per_partid[request.partid]
        group_counters = self._interval_per_group[
            (request.partid, request.pmg)
        ]
        for target in (counters, group_counters):
            target["requests"] += 1
            target["bytes"] += request.size_bytes
            target["queue_delay_ns"] += queue_delay
            target["service_delay_ns"] += service_delay
            target["grants"] += 1
            if request.mc_arbitration.bmin_promoted:
                target["bmin_priority_requests"] += 1
            if request.mc_arbitration.soft_over_limit:
                target["softlimit_requests"] += 1
                target["softlimit_bytes"] += request.size_bytes
            if request.mc_arbitration.soft_demoted:
                target["softlimit_penalty_events"] += 1
            raw_effective_qos = (
                request.mc_arbitration.raw_effective_qos
            )
            target["raw_effective_qos_sum"] += raw_effective_qos
            target["raw_effective_qos_min"] = min(
                target["raw_effective_qos_min"],
                raw_effective_qos,
            )
            target["raw_effective_qos_max"] = max(
                target["raw_effective_qos_max"],
                raw_effective_qos,
            )
            effective_qos = request.mc_arbitration.effective_qos
            target["effective_qos_sum"] += effective_qos
            target["effective_qos_min"] = min(
                target["effective_qos_min"],
                effective_qos,
            )
            target["effective_qos_max"] = max(
                target["effective_qos_max"],
                effective_qos,
            )
            target["qos_promoted_requests"] += int(
                request.mc_arbitration.bmin_promoted
            )
            target["qos_demoted_requests"] += int(
                request.mc_arbitration.soft_demoted
            )
            target["bmin_qos_delta_sum"] += (
                request.mc_arbitration.bmin_qos_delta
            )
            target["softlimit_qos_delta_sum"] += (
                request.mc_arbitration.softlimit_qos_delta
            )
            target["bmin_error_ratio_sum"] += (
                request.mc_arbitration.bmin_error_ratio
            )
            target["bmax_error_ratio_sum"] += (
                request.mc_arbitration.bmax_error_ratio
            )
            target["qos_error_weighted_requests"] += int(
                request.mc_arbitration.qos_adjust_mode
                == "error_weighted"
            )
            target["qos_aging_promotions"] += (
                request.mc_arbitration.aging_steps
            )
            target["qos_mapping_events"] += int(
                request.mc_arbitration.qos_mapping_enabled
                and raw_effective_qos != effective_qos
            )
            unclamped = (
                request.mc_arbitration.base_qos
                + request.mc_arbitration.bmin_qos_delta
                - request.mc_arbitration.softlimit_qos_delta
                + request.mc_arbitration.aging_steps
            )
            target["qos_saturation_events"] += int(
                unclamped < 0 or unclamped > 7
            )

        self._interval_busy_ns += serialization_ns
        self._interval_requests += 1
        self._interval_bytes += request.size_bytes
        self._monitor_cumulative_bytes[request.partid] = (
            self._monitor_cumulative_bytes[request.partid]
            + request.size_bytes
        ) % self.MONITOR_COUNTER_MODULUS
        self._sample_queue()

        self.kernel.schedule(
            service_delay,
            lambda: self._complete_request(request),
            f"mc-complete:{self.component_id}",
        )
        self._schedule_dispatch(serialization_ns)

    def _complete_request(self, request: Request) -> None:
        level = self._cbusy_level[request.partid]
        request.return_cbusy_source = self.component_id
        request.return_cbusy_level = level
        request.return_cbusy_ostd_cap = (
            self._cbusy_cap(request.partid, level)
            if level > 0
            else 0
        )
        request.return_cbusy_sample_time_ns = (
            self._cbusy_sample_time_ns.get(
                request.partid,
                self.kernel.now_ns,
            )
        )
        request.return_cbusy_monitor_sample_id = (
            self._cbusy_monitor_sample_id.get(request.partid, "")
        )
        request.return_cbusy_decision_id = (
            self._cbusy_decision_id.get(request.partid, "")
        )
        self.on_complete(request)

    def _configured_partids(self) -> set[int]:
        return {partid for partid, _ in self.settings.items()}

    def _known_partids(self) -> List[int]:
        pending = {
            entry.request.partid
            for entry in self._buffer
            if entry is not None
        }
        return sorted(
            self._configured_partids()
            | pending
            | set(self._monitor_cumulative_bytes)
            | set(self._monitor_last_sample_bytes)
            | set(self._filtered_bandwidth_gbps)
            | set(self._control_bandwidth_gbps)
            | set(self._cbusy_level)
        )

    def _update_limit_states(
        self,
        partid: int,
        filtered_gbps: float,
    ) -> Tuple[Dict[str, bool], Dict[str, bool]]:
        old_state = {
            "under_bmin": bool(self._under_bmin[partid]),
            "over_bmax": bool(self._over_bmax[partid]),
            "hard_block": bool(self._hard_block[partid]),
        }
        setting = self.settings.lookup(partid)
        hysteresis = self.config.bandwidth_hysteresis
        if (
            not self.enforce_controls
            or not setting.bmin_enable
            or setting.bw_min_gbps is None
            or setting.bw_min_gbps <= 0
        ):
            self._under_bmin[partid] = False
        elif self._under_bmin[partid]:
            self._under_bmin[partid] = (
                filtered_gbps
                < setting.bw_min_gbps * (1.0 + hysteresis)
            )
        else:
            self._under_bmin[partid] = (
                filtered_gbps < setting.bw_min_gbps
            )

        if (
            not self.enforce_controls
            or not setting.bmax_enable
            or setting.bw_max_gbps is None
            or setting.bw_max_gbps <= 0
        ):
            self._over_bmax[partid] = False
        elif self._over_bmax[partid]:
            self._over_bmax[partid] = (
                filtered_gbps
                > setting.bw_max_gbps * (1.0 - hysteresis)
            )
        else:
            self._over_bmax[partid] = (
                filtered_gbps > setting.bw_max_gbps
            )
        self._hard_block[partid] = bool(
            self._over_bmax[partid]
            and setting.bw_limit_mode == "hardlimit"
            and setting.bmax_enable
            and self.enforce_controls
        )
        new_state = {
            "under_bmin": bool(self._under_bmin[partid]),
            "over_bmax": bool(self._over_bmax[partid]),
            "hard_block": bool(self._hard_block[partid]),
        }
        return old_state, new_state

    def _publish_bandwidth_monitor(self) -> None:
        period_ns = self.monitor_period_ns
        weight_sum = (
            self.config.history_weight
            + self.config.current_weight
        )
        partids = self._known_partids()
        local_cycle = int(
            self.kernel.now_ns * self.config.clock_mhz / 1000.0
        )
        for partid in partids:
            cumulative = self._monitor_cumulative_bytes[partid]
            previous_cumulative = self._monitor_last_sample_bytes[partid]
            delta_bytes = (
                cumulative - previous_cumulative
            ) % self.MONITOR_COUNTER_MODULUS
            raw = (
                delta_bytes
                * 8.0
                / period_ns
            )
            previous = self._filtered_bandwidth_gbps[partid]
            filtered = (
                self.config.history_weight * previous
                + self.config.current_weight * raw
            ) / weight_sum
            self._monitor_delta_bytes[partid] = delta_bytes
            self._monitor_last_sample_bytes[partid] = cumulative
            self._raw_bandwidth_gbps[partid] = raw
            self._filtered_bandwidth_gbps[partid] = filtered
            self._control_bandwidth_gbps[partid] = filtered
            self._monitor_updates[partid] += 1
            old_state, new_state = self._update_limit_states(
                partid,
                filtered,
            )
            self._publish_limit_state_event(
                partid,
                old_state,
                new_state,
                filtered,
                local_cycle,
            )
            if self._hard_block[partid]:
                blocked = [
                    entry
                    for entry in self._buffer
                    if (
                        entry is not None
                        and entry.request.partid == partid
                    )
                ]
                if blocked:
                    counters = self._interval_per_partid[partid]
                    counters["hardlimit_block_events"] += 1
                    counters["throttle_delay_ns"] += (
                        len(blocked) * period_ns
                    )
                    for entry in blocked:
                        entry.request.throttle_delay_ns += period_ns
                        group = self._interval_per_group[
                            (partid, entry.request.pmg)
                        ]
                        group["hardlimit_block_events"] += 1
                        group["throttle_delay_ns"] += period_ns
        self._schedule_dispatch(0.0)
        self.kernel.schedule(
            period_ns,
            self._publish_bandwidth_monitor,
            f"mc-monitor:{self.component_id}",
        )

    def _publish_limit_state_event(
        self,
        partid: int,
        old_state: Dict[str, bool],
        new_state: Dict[str, bool],
        control_bandwidth: float,
        local_cycle: int,
    ) -> None:
        if self.on_control_event is None or old_state == new_state:
            return
        setting = self.settings.lookup(partid)
        monitor_sample_id = (
            f"{self.component_id}:mc_control_input:"
            f"{local_cycle}:partid:{partid}"
        )
        if new_state["hard_block"] or new_state["over_bmax"]:
            outcome_state = "overshoot"
        elif new_state["under_bmin"]:
            outcome_state = "unmet"
        else:
            outcome_state = "met"
        self.on_control_event(
            resource_id=self.component_id,
            partid=partid,
            event_type="limit_state_changed",
            field="mc_bmin_bmax_state",
            old_state=old_state,
            new_state=new_state,
            policy="mc_bmin_bmax",
            reason=(
                "latched bandwidth control input updates "
                "BMIN/BMAX state"
            ),
            monitor_sample_id=monitor_sample_id,
            decision_id=(
                f"decision:{monitor_sample_id}:mc_bmin_bmax"
            ),
            action_effective_time_ns=self.kernel.now_ns,
            details={
                "local_cycle": local_cycle,
                "control_input_metric": "control_bandwidth_gbps",
                "control_input_value": control_bandwidth,
                "control_input_unit": "Gbps",
                "latest_filtered_bandwidth_gbps": (
                    self._filtered_bandwidth_gbps[partid]
                ),
                "bmin_gbps": setting.bw_min_gbps,
                "bmax_gbps": setting.bw_max_gbps,
                "limit_mode": setting.bw_limit_mode,
                "bandwidth_hysteresis": self.config.bandwidth_hysteresis,
            },
            outcome_state=outcome_state,
            outcome_reason=(
                "BMAX exceeded"
                if new_state["over_bmax"]
                else "below BMIN"
                if new_state["under_bmin"]
                else "limit state released"
            ),
        )

    def _update_service_deficit(self) -> None:
        max_counter = (1 << self.config.aging_counter_bits) - 1
        ready_partids = {
            entry.request.partid
            for entry in self._ready_entries()
        }
        for partid in self._known_partids():
            if (
                partid not in ready_partids
                or self._hard_block[partid]
            ):
                self._service_deficit[partid] = 0
            elif self._grant_seen[partid]:
                self._service_deficit[partid] = max(
                    0,
                    self._service_deficit[partid] - 1,
                )
            else:
                self._service_deficit[partid] = min(
                    max_counter,
                    self._service_deficit[partid] + 1,
                )
            self._grant_seen[partid] = False
        self._schedule_dispatch(0.0)
        self.kernel.schedule(
            self.aging_quantum_ns,
            self._update_service_deficit,
            f"mc-deficit:{self.component_id}",
        )

    def _sample_queue(self) -> None:
        self._queue_sample_sum += self.queue_length
        self._queue_samples += 1
        self._peak_queue_length = max(
            self._peak_queue_length,
            self.queue_length,
        )

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
    ) -> int:
        setting = self.settings.lookup(partid)
        if (
            not self.enforce_controls
            or not setting.cbusy_enable
        ):
            return 0
        ready_partids = {
            entry.request.partid
            for entry in self._ready_entries()
        }
        contended = len(ready_partids) >= 2
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
        if self._hard_block[partid]:
            level = max(level, 2)
        return level

    def _evaluate_cbusy(self) -> None:
        sample_ns = self.config.cbusy_sample_ns
        self._cbusy_sample_index += 1
        for partid in self._known_partids():
            self._cbusy_sample_time_ns[partid] = self.kernel.now_ns
            self._cbusy_monitor_sample_id[partid] = (
                f"mc_cbusy_sample:{self.component_id}:"
                f"{self._cbusy_sample_index}:partid:{partid}"
            )
            self._cbusy_decision_id[partid] = (
                f"decision:mc_cbusy:{self.component_id}:"
                f"{self._cbusy_sample_index}:partid:{partid}"
            )
            setting = self.settings.lookup(partid)
            bandwidth_ratio = (
                self._control_bandwidth_gbps[partid]
                / setting.bw_max_gbps
                if (
                    setting.bmax_enable
                    and setting.bw_max_gbps is not None
                    and setting.bw_max_gbps > 0
                )
                else 0.0
            )
            queue_ratio = (
                self._partid_buffer_count(partid)
                / max(1, self.config.queue_depth)
            )
            detected = self._detected_cbusy_level(
                partid,
                bandwidth_ratio,
                queue_ratio,
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

        self.kernel.schedule(
            sample_ns,
            self._evaluate_cbusy,
            f"cbusy-sample:{self.component_id}",
        )

    def monitor_snapshot(self, interval_ns: float):
        utilization = min(
            1.0,
            self._interval_busy_ns / max(interval_ns, 1e-9),
        )
        partids = sorted(
            self._configured_partids()
            | set(self._interval_per_partid)
            | set(self._filtered_bandwidth_gbps)
            | set(self._control_bandwidth_gbps)
        )
        per_partid = {}
        for partid in partids:
            values = dict(self._interval_per_partid[partid])
            setting = self.settings.lookup(partid)
            requests = int(values["requests"])
            effective_qos_avg = (
                values["effective_qos_sum"] / requests
                if requests
                else 0.0
            )
            raw_effective_qos_avg = (
                values["raw_effective_qos_sum"] / requests
                if requests
                else 0.0
            )
            bmax = (
                setting.bw_max_gbps
                if self.enforce_controls and setting.bmax_enable
                else None
            )
            bmin = (
                setting.bw_min_gbps
                if self.enforce_controls and setting.bmin_enable
                else None
            )
            per_partid[str(partid)] = {
                **values,
                "achieved_bandwidth_gbps": (
                    values["bytes"]
                    * 8.0
                    / max(interval_ns, 1e-9)
                ),
                "raw_bandwidth_gbps": self._raw_bandwidth_gbps[partid],
                "filtered_bandwidth_gbps": (
                    self._filtered_bandwidth_gbps[partid]
                ),
                "control_bandwidth_gbps": (
                    self._control_bandwidth_gbps[partid]
                ),
                "monitor_cumulative_bytes_63b": (
                    self._monitor_cumulative_bytes[partid]
                ),
                "monitor_delta_bytes": self._monitor_delta_bytes[partid],
                "bmax_gbps": bmax,
                "bmin_gbps": bmin,
                "bmax_assert_gbps": bmax,
                "bmax_release_gbps": (
                    bmax * (1.0 - self.config.bandwidth_hysteresis)
                    if bmax is not None
                    else None
                ),
                "bmin_assert_gbps": bmin,
                "bmin_release_gbps": (
                    bmin * (1.0 + self.config.bandwidth_hysteresis)
                    if bmin is not None
                    else None
                ),
                "under_bmin": self._under_bmin[partid],
                "over_bmax": self._over_bmax[partid],
                "hard_block": self._hard_block[partid],
                "limit_mode": (
                    setting.bw_limit_mode
                    if self.enforce_controls
                    else "disabled"
                ),
                "base_qos": (
                    setting.mc_qos
                    if self.enforce_controls and setting.mc_qos_enable
                    else 0
                ),
                "raw_effective_qos_avg": raw_effective_qos_avg,
                "raw_effective_qos_min": (
                    values["raw_effective_qos_min"] if requests else 0
                ),
                "raw_effective_qos_max": (
                    values["raw_effective_qos_max"] if requests else 0
                ),
                "effective_qos_avg": effective_qos_avg,
                "effective_qos_min": (
                    values["effective_qos_min"] if requests else 0
                ),
                "effective_qos_max": (
                    values["effective_qos_max"] if requests else 0
                ),
                "qos_adjust_mode": self.config.qos_adjust_mode,
                "bmin_qos_delta_avg": (
                    values["bmin_qos_delta_sum"] / requests
                    if requests
                    else 0.0
                ),
                "softlimit_qos_delta_avg": (
                    values["softlimit_qos_delta_sum"] / requests
                    if requests
                    else 0.0
                ),
                "bmin_error_ratio_avg": (
                    values["bmin_error_ratio_sum"] / requests
                    if requests
                    else 0.0
                ),
                "bmax_error_ratio_avg": (
                    values["bmax_error_ratio_sum"] / requests
                    if requests
                    else 0.0
                ),
                "qos_error_weighted_requests": (
                    values["qos_error_weighted_requests"]
                ),
                "qos_map_8_to_4_enable": (
                    self.config.qos_map_8_to_4_enable
                ),
                "qos_mapping_events": values["qos_mapping_events"],
                "service_deficit": self._service_deficit[partid],
                "service_deficit_qos_steps": (
                    self._deficit_qos_steps(partid)
                ),
                "monitor_updates": self._monitor_updates[partid],
                "buffer_entries": self._partid_buffer_count(partid),
                "buffer_ratio": (
                    self._partid_buffer_count(partid)
                    / max(1, self.config.queue_depth)
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
                "cbusy_ostd_cap": (
                    self._cbusy_cap(
                        partid,
                        self._cbusy_level[partid],
                    )
                    if self._cbusy_level[partid] > 0
                    else None
                ),
                "cbusy_l1_ostd": setting.cbusy_l1_ostd,
                "cbusy_l2_ostd": setting.cbusy_l2_ostd,
                "cbusy_l3_ostd": setting.cbusy_l3_ostd,
                "monitor_enable": setting.monitor_enable,
                "enforcement_enabled": self.enforce_controls,
            }

        monitor_groups = {}
        for partid, pmg in sorted(self._interval_per_group):
            values = dict(self._interval_per_group[(partid, pmg)])
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
                "raw_bandwidth_gbps": self._raw_bandwidth_gbps[partid],
                "filtered_bandwidth_gbps": (
                    self._filtered_bandwidth_gbps[partid]
                ),
                "control_bandwidth_gbps": (
                    self._control_bandwidth_gbps[partid]
                ),
                "monitor_cumulative_bytes_63b": (
                    self._monitor_cumulative_bytes[partid]
                ),
                "monitor_delta_bytes": self._monitor_delta_bytes[partid],
                "controller_bandwidth_gbps": self.total_bandwidth_gbps,
                "bandwidth_utilization": min(
                    1.0,
                    bandwidth / max(self.total_bandwidth_gbps, 1e-9),
                ),
                "bmax_gbps": (
                    setting.bw_max_gbps
                    if self.enforce_controls and setting.bmax_enable
                    else None
                ),
                "bmin_gbps": (
                    setting.bw_min_gbps
                    if self.enforce_controls and setting.bmin_enable
                    else None
                ),
                "limit_mode": (
                    setting.bw_limit_mode
                    if self.enforce_controls
                    else "disabled"
                ),
                "base_qos": (
                    setting.mc_qos
                    if self.enforce_controls and setting.mc_qos_enable
                    else 0
                ),
                "raw_effective_qos_avg": (
                    values["raw_effective_qos_sum"] / requests
                    if requests
                    else 0.0
                ),
                "raw_effective_qos_min": (
                    values["raw_effective_qos_min"] if requests else 0
                ),
                "raw_effective_qos_max": (
                    values["raw_effective_qos_max"] if requests else 0
                ),
                "effective_qos_avg": (
                    values["effective_qos_sum"] / requests
                    if requests
                    else 0.0
                ),
                "effective_qos_min": (
                    values["effective_qos_min"] if requests else 0
                ),
                "effective_qos_max": (
                    values["effective_qos_max"] if requests else 0
                ),
                "qos_adjust_mode": self.config.qos_adjust_mode,
                "bmin_qos_delta_avg": (
                    values["bmin_qos_delta_sum"] / requests
                    if requests
                    else 0.0
                ),
                "softlimit_qos_delta_avg": (
                    values["softlimit_qos_delta_sum"] / requests
                    if requests
                    else 0.0
                ),
                "bmin_error_ratio_avg": (
                    values["bmin_error_ratio_sum"] / requests
                    if requests
                    else 0.0
                ),
                "bmax_error_ratio_avg": (
                    values["bmax_error_ratio_sum"] / requests
                    if requests
                    else 0.0
                ),
                "qos_error_weighted_requests": (
                    values["qos_error_weighted_requests"]
                ),
                "qos_map_8_to_4_enable": (
                    self.config.qos_map_8_to_4_enable
                ),
                "qos_mapping_events": values["qos_mapping_events"],
                "under_bmin": self._under_bmin[partid],
                "over_bmax": self._over_bmax[partid],
                "hard_block": self._hard_block[partid],
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
            "queue_peak": self._peak_queue_length,
            "queue_depth": self.config.queue_depth,
            "bytes": self._interval_bytes,
            "requests": self._interval_requests,
            "clock_mhz": self.config.clock_mhz,
            "monitor_period_cycles": self.config.monitor_period_cycles,
            "monitor_period_ns": self.monitor_period_ns,
            "history_weight": self.config.history_weight,
            "current_weight": self.config.current_weight,
            "bandwidth_hysteresis": self.config.bandwidth_hysteresis,
            "aging_mode": self.config.aging_mode,
            "aging_quantum_cycles": self.config.aging_quantum_cycles,
            "aging_counter_bits": self.config.aging_counter_bits,
            "qos_aging_max_steps": self.config.qos_aging_max_steps,
            "qos_adjust_mode": self.config.qos_adjust_mode,
            "bmin_qos_promote": self.config.bmin_qos_promote,
            "softlimit_qos_demote": self.config.softlimit_qos_demote,
            "bmin_error_weight": self.config.bmin_error_weight,
            "bmax_error_weight": self.config.bmax_error_weight,
            "qos_error_deadband_percent": (
                self.config.qos_error_deadband_percent
            ),
            "qos_error_max_delta": self.config.qos_error_max_delta,
            "qos_error_quantization": (
                self.config.qos_error_quantization
            ),
            "qos_map_8_to_4_enable": (
                self.config.qos_map_8_to_4_enable
            ),
            "enforcement_enabled": self.enforce_controls,
            "per_partid": per_partid,
            "monitor_groups": monitor_groups,
        }
        self._interval_busy_ns = 0.0
        self._interval_requests = 0
        self._interval_bytes = 0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._peak_queue_length = self.queue_length
        self._interval_per_partid.clear()
        self._interval_per_group.clear()
        self._cbusy_interval_transitions.clear()
        self._cbusy_interval_assertions.clear()
        self._cbusy_interval_active_ns.clear()
        self._cbusy_interval_peak_bw_ratio.clear()
        self._cbusy_interval_peak_queue_ratio.clear()
        return self.build_monitor_snapshot(
            self.kernel.now_ns,
            interval_ns,
            row,
            local_cycle=int(
                self.kernel.now_ns * self.config.clock_mhz / 1000.0
            ),
        )
