from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, DefaultDict, Deque, Dict, List, Optional, Tuple

from src.config.schema import CacheConfig
from src.mpam.settings import MPAMSetting, SettingsTable
from src.sim.component import Component
from src.sim.kernel import SimulationKernel
from src.traffic.request import Request


@dataclass
class CacheLine:
    valid: bool = False
    tag: int = 0
    owner_partid: Optional[int] = None
    owner_pmg: Optional[int] = None
    last_touch: int = 0


@dataclass
class MshrWaiter:
    request: Request
    joined_time_ns: float
    owner: bool = False


@dataclass
class MshrEntry:
    transaction_id: int
    line_address: int
    owner_request: Request
    waiters: List[MshrWaiter] = field(default_factory=list)


def _cache_counters() -> Dict[str, float]:
    return {
        "requests": 0,
        "hits": 0,
        "misses": 0,
        "bytes": 0,
        "delay_ns": 0.0,
        "sampled_requests": 0,
        "sampled_bytes": 0,
        "allocation_denials": 0,
        "allocation_bypass": 0,
        "cmin_protected_evictions": 0,
        "cmax_growth_blocks": 0,
        "cpbm_excluded_ways": 0,
        "evictions": 0,
        "self_replacements": 0,
        "merged_misses": 0,
        "mshr_allocations": 0,
        "mshr_full_events": 0,
        "cbusy_mshr_blocks": 0,
        "fill_completions": 0,
        "fill_buffer_full_events": 0,
        "redundant_memory_fetches": 0,
        "queue_delay_ns": 0.0,
        "admission_backpressure_ns": 0.0,
        "queue_full_events": 0,
    }


class CacheMSC(Component):
    capabilities = (
        "cache_lookup_pipeline",
        "explicit_full_tag_array",
        "lru_replacement",
        "tree_plru_replacement",
        "mshr_same_line_read_merge",
        "fill_buffer",
        "sampled_owner_monitoring",
        "actual_occupancy_monitoring",
        "cpbm_control",
        "cmin_control",
        "cmax_control",
        "cbusy_mshr_response",
    )
    required_monitors = (
        "actual_occupancy",
        "sampled_occupancy",
        "queue_occupancy",
        "mshr_occupancy",
        "fill_buffer_occupancy",
        "hit_miss",
    )
    actions = (
        "admit",
        "lookup_tag",
        "merge_or_allocate_mshr",
        "accept_fill",
        "select_victim",
        "allocate_line",
        "complete_waiters",
    )
    validation_hooks = (
        "queue_capacity",
        "mshr_capacity",
        "fill_buffer_capacity",
        "unique_tag_per_set",
        "cpbm_reachability",
        "cmin_cmax_order",
    )
    incompatible_capabilities = ("probabilistic_cache_hit",)
    approximations = (
        "sparse allocation of untouched all-invalid sets",
        "sampled-owner counter bank per set-group offset",
        "configurable fixed or rotating sampled-owner offset",
    )

    def __init__(
        self,
        kernel: SimulationKernel,
        config: CacheConfig,
        settings: SettingsTable,
        seed: int,
        on_hit: Callable[[Request], None],
        on_miss: Callable[[Request], None],
        enforce_controls: bool = True,
        on_control_event: Optional[Callable[..., None]] = None,
    ) -> None:
        super().__init__(config.id, "cache")
        self.kernel = kernel
        self.config = config
        self.settings = settings
        self.on_hit = on_hit
        self.on_miss = on_miss
        self.enforce_controls = enforce_controls
        self.on_control_event = on_control_event
        self._queue: Deque[Request] = deque()
        self._active_lookups = 0
        self._interval_lookup_busy_ns = 0.0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._queue_peak = 0
        self._active_peak = 0
        self._touch_sequence = 0
        self._sets: Dict[int, List[CacheLine]] = {}
        self._plru_bits: Dict[int, List[int]] = {}
        self._mshrs: Dict[int, MshrEntry] = {}
        self._mshr_by_line: DefaultDict[int, List[int]] = defaultdict(list)
        self._mshr_wait_queue: Deque[Tuple[Request, float]] = deque()
        self._mshr_peak = 0
        self._fill_buffer_occupancy = 0
        self._fill_buffer_peak = 0
        self._interval: DefaultDict[
            int, Dict[str, float]
        ] = defaultdict(_cache_counters)
        self._interval_groups: DefaultDict[
            Tuple[int, int], Dict[str, float]
        ] = defaultdict(_cache_counters)
        self._monitor_sampled_bytes: DefaultDict[int, int] = defaultdict(int)
        self._sampled_owner_counters: DefaultDict[
            int, DefaultDict[int, int]
        ] = defaultdict(lambda: defaultdict(int))
        self._sampled_group_owner_counters: DefaultDict[
            int, DefaultDict[Tuple[int, int], int]
        ] = defaultdict(lambda: defaultdict(int))
        self._raw_sampled_counts: DefaultDict[int, float] = defaultdict(float)
        self._filtered_sampled_counts: DefaultDict[
            int, float
        ] = defaultdict(float)
        self._control_sampled_counts: DefaultDict[
            int, float
        ] = defaultdict(float)
        self._raw_sampled_bandwidth_gbps: DefaultDict[
            int, float
        ] = defaultdict(float)
        self._filtered_sampled_bandwidth_gbps: DefaultDict[
            int, float
        ] = defaultdict(float)
        self._monitor_updates: DefaultDict[int, int] = defaultdict(int)
        self._monitor_cycle_index = 0
        self._sampling_offset = 0
        self._last_sampling_offset = 0
        self._control_state_by_partid: Dict[int, Dict[str, bool]] = {}
        self._cbusy_level_by_partid: DefaultDict[int, int] = defaultdict(int)
        self._cbusy_mshr_cap_by_partid: DefaultDict[int, int] = defaultdict(
            lambda: self.config.mshr_entries
        )
        self._cbusy_transitions_by_partid: DefaultDict[int, int] = (
            defaultdict(int)
        )
        self.kernel.schedule(
            self.monitor_period_ns,
            self._publish_mpam_monitor,
            f"l3-monitor:{self.component_id}",
        )

    @property
    def monitor_period_ns(self) -> float:
        return (
            self.config.monitor_period_cycles
            * 1000.0
            / self.config.clock_mhz
        )

    @property
    def mshr_occupancy(self) -> int:
        return len(self._mshrs)

    @property
    def fill_buffer_occupancy(self) -> int:
        return self._fill_buffer_occupancy

    def _cbusy_response_enabled(self, partid: int) -> bool:
        setting = self.settings.lookup(partid)
        return bool(
            self.enforce_controls
            and self.config.cbusy_response_enable
            and setting.cbusy_enable
        )

    def _cbusy_level(self, partid: int) -> int:
        return self._cbusy_level_by_partid.get(partid, 0)

    def _cbusy_mshr_cap(
        self,
        partid: int,
        level: Optional[int] = None,
    ) -> int:
        if not self._cbusy_response_enabled(partid):
            return self.config.mshr_entries
        effective_level = (
            self._cbusy_level(partid) if level is None else level
        )
        if effective_level <= 0:
            return self.config.mshr_entries
        setting = self.settings.lookup(partid)
        cap = {
            1: setting.cbusy_l1_ostd,
            2: setting.cbusy_l2_ostd,
            3: setting.cbusy_l3_ostd,
        }.get(effective_level, setting.cbusy_l3_ostd)
        return max(1, min(self.config.mshr_entries, int(cap)))

    def _partid_mshr_occupancy(self, partid: int) -> int:
        return sum(
            1
            for entry in self._mshrs.values()
            if entry.owner_request.partid == partid
        )

    def _cbusy_blocks_mshr(self, request: Request) -> bool:
        if not self._cbusy_response_enabled(request.partid):
            return False
        level = self._cbusy_level(request.partid)
        if level <= 0:
            return False
        return (
            self._partid_mshr_occupancy(request.partid)
            >= self._cbusy_mshr_cap(request.partid, level)
        )

    def receive(self, request: Request) -> None:
        request.cache_id = self.component_id
        if not self.can_accept(request):
            retry_ns = 2.0
            request.cache_queue_delay_ns += retry_ns
            request.cache_delay_ns += retry_ns
            self._increment(
                request,
                "admission_backpressure_ns",
                retry_ns,
            )
            self._increment(request, "queue_full_events")
            self.kernel.schedule(
                retry_ns,
                lambda: self.receive(request),
                "cache-admission-retry",
            )
            return
        request.cache_enqueue_time_ns = self.kernel.now_ns
        self._queue.append(request)
        self._sample_queue()
        self._dispatch()

    def can_accept(self, request: Request) -> bool:
        return len(self._queue) < self.config.queue_depth

    def accept(self, request: Request) -> None:
        self.receive(request)

    def lookup(self, request: Request) -> None:
        self.receive(request)

    def can_accept_fill(self, request: Request) -> bool:
        ready = (
            self._fill_buffer_occupancy
            < self.config.fill_buffer_entries
        )
        if not ready:
            self._increment(request, "fill_buffer_full_events")
        return ready

    def accept_fill(self, request: Request) -> None:
        self._fill_buffer_occupancy += 1
        self._fill_buffer_peak = max(
            self._fill_buffer_peak,
            self._fill_buffer_occupancy,
        )
        self.kernel.schedule(
            self.config.fill_latency_ns,
            lambda: self._finish_fill(request),
            f"l3-fill:{self.component_id}",
        )

    def _increment(
        self,
        request: Request,
        field: str,
        amount: float = 1.0,
    ) -> None:
        self._interval[request.partid][field] += amount
        self._interval_groups[
            (request.partid, request.pmg)
        ][field] += amount

    def _dispatch(self) -> None:
        while (
            self._queue
            and self._active_lookups < self.config.lookup_parallelism
        ):
            request = self._queue.popleft()
            queue_delay = max(
                0.0,
                self.kernel.now_ns - request.cache_enqueue_time_ns,
            )
            request.cache_queue_delay_ns += queue_delay
            request.cache_delay_ns += queue_delay
            self._increment(request, "queue_delay_ns", queue_delay)
            self._active_lookups += 1
            self._active_peak = max(
                self._active_peak,
                self._active_lookups,
            )
            self._sample_queue()
            self._start_lookup(request)

    def _start_lookup(self, request: Request) -> None:
        set_index = self._set_index(request.addr)
        tag = self._tag(request.addr)
        ways = self._set_ways(set_index)
        hit_way = next(
            (
                index
                for index, line in enumerate(ways)
                if line.valid and line.tag == tag
            ),
            None,
        )
        is_hit = hit_way is not None
        request.cache_hit = is_hit
        latency = (
            self.config.hit_latency_ns
            if is_hit
            else self.config.miss_detect_latency_ns
        )
        request.cache_delay_ns += latency
        self._increment(request, "requests")
        self._increment(request, "bytes", request.size_bytes)
        self._increment(request, "delay_ns", latency)
        self._increment(request, "hits" if is_hit else "misses")
        if self._is_sample_set(set_index):
            self._increment(request, "sampled_requests")
            self._increment(
                request,
                "sampled_bytes",
                request.size_bytes,
            )
            self._monitor_sampled_bytes[request.partid] += (
                request.size_bytes
            )
        self._interval_lookup_busy_ns += latency
        self.kernel.schedule(
            latency,
            lambda: self._finish_lookup(
                request,
                set_index,
                hit_way,
            ),
            "cache-result",
        )

    def _finish_lookup(
        self,
        request: Request,
        set_index: int,
        hit_way: Optional[int],
    ) -> None:
        self._active_lookups = max(0, self._active_lookups - 1)
        if hit_way is not None:
            self._touch(set_index, hit_way)
            self.on_hit(request)
        else:
            self._handle_miss(request)
        self._sample_queue()
        self._dispatch()

    def _handle_miss(self, request: Request) -> None:
        line_address = self._line_address(request.addr)
        if (
            self.config.merge_same_line_misses
            and request.op == "read"
        ):
            for transaction_id in self._mshr_by_line[line_address]:
                entry = self._mshrs.get(transaction_id)
                if (
                    entry is not None
                    and entry.owner_request.op == "read"
                ):
                    entry.waiters.append(
                        MshrWaiter(
                            request=request,
                            joined_time_ns=self.kernel.now_ns,
                        )
                    )
                    self._increment(request, "merged_misses")
                    return
        if self.mshr_occupancy >= self.config.mshr_entries:
            self._mshr_wait_queue.append(
                (request, self.kernel.now_ns)
            )
            self._increment(request, "mshr_full_events")
            return
        if self._cbusy_blocks_mshr(request):
            self._mshr_wait_queue.append(
                (request, self.kernel.now_ns)
            )
            self._increment(request, "cbusy_mshr_blocks")
            return
        self._allocate_mshr(request)

    def _allocate_mshr(self, request: Request) -> None:
        line_address = self._line_address(request.addr)
        entry = MshrEntry(
            transaction_id=request.transaction_id,
            line_address=line_address,
            owner_request=request,
            waiters=[
                MshrWaiter(
                    request=request,
                    joined_time_ns=self.kernel.now_ns,
                    owner=True,
                )
            ],
        )
        self._mshrs[entry.transaction_id] = entry
        self._mshr_by_line[line_address].append(
            entry.transaction_id
        )
        self._mshr_peak = max(
            self._mshr_peak,
            self.mshr_occupancy,
        )
        self._increment(request, "mshr_allocations")
        self.on_miss(request)

    def _finish_fill(self, request: Request) -> None:
        self._fill_buffer_occupancy = max(
            0,
            self._fill_buffer_occupancy - 1,
        )
        entry = self._mshrs.pop(request.transaction_id, None)
        if entry is None:
            raise RuntimeError(
                "L3 fill completed without matching MSHR: "
                f"{request.transaction_id}"
            )
        transaction_ids = self._mshr_by_line[entry.line_address]
        transaction_ids.remove(entry.transaction_id)
        if not transaction_ids:
            del self._mshr_by_line[entry.line_address]

        self._observe_return_cbusy(entry.owner_request)
        self._allocate_fill(entry.owner_request)
        self._increment(entry.owner_request, "fill_completions")
        for waiter in entry.waiters:
            if waiter.owner:
                delay = self.config.fill_latency_ns
            else:
                delay = max(
                    0.0,
                    self.kernel.now_ns - waiter.joined_time_ns,
                )
                waiter.request.return_cbusy_source = (
                    entry.owner_request.return_cbusy_source
                )
                waiter.request.return_cbusy_level = (
                    entry.owner_request.return_cbusy_level
                )
                waiter.request.return_cbusy_ostd_cap = (
                    entry.owner_request.return_cbusy_ostd_cap
                )
                waiter.request.return_cbusy_sample_time_ns = (
                    entry.owner_request.return_cbusy_sample_time_ns
                )
                waiter.request.return_cbusy_monitor_sample_id = (
                    entry.owner_request.return_cbusy_monitor_sample_id
                )
                waiter.request.return_cbusy_decision_id = (
                    entry.owner_request.return_cbusy_decision_id
                )
            waiter.request.timing.mshr_fill_delay_ns += delay
            waiter.request.cache_delay_ns += self.config.fill_latency_ns
            self.on_hit(waiter.request)
        self._drain_mshr_wait_queue()

    def _drain_mshr_wait_queue(self) -> None:
        attempts = len(self._mshr_wait_queue)
        for _ in range(attempts):
            if (
                not self._mshr_wait_queue
                or self.mshr_occupancy >= self.config.mshr_entries
            ):
                break
            request, wait_start = self._mshr_wait_queue.popleft()
            request.timing.mshr_fill_delay_ns += max(
                0.0,
                self.kernel.now_ns - wait_start,
            )
            self._handle_miss(request)

    def _observe_return_cbusy(self, request: Request) -> None:
        partid = request.partid
        if not self._cbusy_response_enabled(partid):
            return
        level = max(0, min(3, int(request.return_cbusy_level or 0)))
        old_level = self._cbusy_level(partid)
        old_cap = self._cbusy_mshr_cap(partid, old_level)
        new_cap = self._cbusy_mshr_cap(partid, level)
        self._cbusy_level_by_partid[partid] = level
        self._cbusy_mshr_cap_by_partid[partid] = new_cap
        if old_level != level:
            self._cbusy_transitions_by_partid[partid] += 1
        if (
            self.on_control_event is None
            or (old_level == level and old_cap == new_cap)
        ):
            return
        monitor_sample_id = (
            f"{self.component_id}:cbusy_return:"
            f"{request.transaction_id}:partid:{partid}"
        )
        self.on_control_event(
            resource_id=self.component_id,
            partid=partid,
            event_type="return_sideband_observed",
            field="l3_cbusy_level",
            old_state=old_level,
            new_state=level,
            policy="l3_cbusy_mshr",
            reason=f"L3 PARTID MSHR cap {new_cap}",
            monitor_sample_id=monitor_sample_id,
            decision_id=f"decision:{monitor_sample_id}:l3_cbusy_mshr",
            action_effective_time_ns=self.kernel.now_ns,
            details={
                "control_input_metric": "return_cbusy_level",
                "control_input_value": level,
                "control_input_unit": "level",
                "transaction_id": request.transaction_id,
                "feedback_source_msc": request.return_cbusy_source,
                "source_monitor_sample_id": (
                    request.return_cbusy_monitor_sample_id
                ),
                "source_decision_id": request.return_cbusy_decision_id,
                "source_sample_time_ns": (
                    request.return_cbusy_sample_time_ns
                ),
                "old_mshr_cap": old_cap,
                "mshr_cap": new_cap,
                "partid_mshr_occupancy": (
                    self._partid_mshr_occupancy(partid)
                ),
                "transport": "rsp_dat_sideband",
                "partid_attribution": "mshr_owner_request",
            },
            outcome_state="active" if level > 0 else "released",
            outcome_reason="L3 CBusy MSHR response updated",
        )

    def _allocate_fill(self, request: Request) -> bool:
        set_index = self._set_index(request.addr)
        tag = self._tag(request.addr)
        ways = self._set_ways(set_index)
        matching = next(
            (
                index
                for index, line in enumerate(ways)
                if line.valid and line.tag == tag
            ),
            None,
        )
        if matching is not None:
            self._increment(request, "redundant_memory_fetches")
            self._touch(set_index, matching)
            return False

        eligible = self._eligible_way_indexes(request.partid)
        self._increment(
            request,
            "cpbm_excluded_ways",
            self.config.ways - len(eligible),
        )
        victim = self._choose_victim(
            set_index,
            ways,
            request.partid,
            eligible,
        )
        if victim is None:
            self._increment(request, "allocation_denials")
            self._increment(request, "allocation_bypass")
            return False

        old_line = ways[victim]
        if old_line.valid:
            self._increment(request, "evictions")
            if old_line.owner_partid == request.partid:
                self._increment(request, "self_replacements")
        self._touch_sequence += 1
        self._update_sampled_owner_counters(
            set_index=set_index,
            old_line=old_line,
            new_partid=request.partid,
            new_pmg=request.pmg,
        )
        ways[victim] = CacheLine(
            valid=True,
            tag=tag,
            owner_partid=request.partid,
            owner_pmg=request.pmg,
            last_touch=self._touch_sequence,
        )
        self._update_plru(set_index, victim)
        return True

    def _choose_victim(
        self,
        set_index: int,
        ways: List[CacheLine],
        partid: int,
        eligible: List[int],
    ) -> Optional[int]:
        if not eligible:
            return None
        setting = self.settings.lookup(partid)
        owner_counts = self._control_owner_counts()
        current_count = owner_counts.get(partid, 0)
        cmax = self._quota_lines(
            self._effective_max_percent(setting),
            round_up=False,
        )
        if current_count >= cmax:
            own = [
                index
                for index in eligible
                if (
                    ways[index].valid
                    and ways[index].owner_partid == partid
                )
            ]
            if not own:
                self._interval[partid]["cmax_growth_blocks"] += 1
                return None
            return self._replacement_candidate(
                set_index,
                ways,
                own,
            )

        empty = [
            index
            for index in eligible
            if not ways[index].valid
        ]
        if empty:
            return empty[0]

        candidates = []
        for index in eligible:
            owner = ways[index].owner_partid
            if owner is None:
                candidates.append(index)
                continue
            owner_setting = self.settings.lookup(owner)
            owner_cmin = self._quota_lines(
                self._effective_min_percent(owner_setting),
                round_up=True,
            )
            if (
                owner_cmin <= 0
                or owner_counts.get(owner, 0) > owner_cmin
            ):
                candidates.append(index)
            else:
                self._interval[partid][
                    "cmin_protected_evictions"
                ] += 1
        if not candidates:
            return None
        return self._replacement_candidate(
            set_index,
            ways,
            candidates,
        )

    def _replacement_candidate(
        self,
        set_index: int,
        ways: List[CacheLine],
        candidates: List[int],
    ) -> int:
        if self.config.replacement_policy == "plru":
            return self._plru_candidate(
                set_index,
                set(candidates),
            )
        return min(
            candidates,
            key=lambda index: ways[index].last_touch,
        )

    def _plru_candidate(
        self,
        set_index: int,
        candidates: set,
    ) -> int:
        bits = self._plru_bits.setdefault(
            set_index,
            [0] * max(0, self.config.ways - 1),
        )

        def choose(node: int, start: int, size: int) -> Optional[int]:
            if size == 1:
                return start if start in candidates else None
            half = size // 2
            preferred_right = bool(bits[node])
            branches = (
                (
                    node * 2 + 2,
                    start + half,
                    preferred_right,
                ),
                (node * 2 + 1, start, not preferred_right),
            )
            for child, child_start, selected in branches:
                if not selected:
                    continue
                result = choose(child, child_start, half)
                if result is not None:
                    return result
            for child, child_start, selected in branches:
                if selected:
                    continue
                result = choose(child, child_start, half)
                if result is not None:
                    return result
            return None

        selected = choose(0, 0, self.config.ways)
        if selected is None:
            raise RuntimeError("PLRU could not select eligible victim")
        return selected

    def _update_plru(self, set_index: int, way_index: int) -> None:
        if self.config.replacement_policy != "plru":
            return
        bits = self._plru_bits.setdefault(
            set_index,
            [0] * max(0, self.config.ways - 1),
        )
        node = 0
        start = 0
        size = self.config.ways
        while size > 1:
            half = size // 2
            went_right = way_index >= start + half
            bits[node] = 0 if went_right else 1
            if went_right:
                start += half
                node = node * 2 + 2
            else:
                node = node * 2 + 1
            size = half

    def _touch(self, set_index: int, way_index: int) -> None:
        self._touch_sequence += 1
        self._set_ways(set_index)[way_index].last_touch = (
            self._touch_sequence
        )
        self._update_plru(set_index, way_index)

    def _sample_queue(self) -> None:
        self._queue_sample_sum += len(self._queue)
        self._queue_samples += 1
        self._queue_peak = max(self._queue_peak, len(self._queue))

    def _set_ways(self, set_index: int) -> List[CacheLine]:
        return self._sets.setdefault(
            set_index,
            [CacheLine() for _ in range(self.config.ways)],
        )

    def _line_address(self, address: int) -> int:
        return address // self.config.line_size

    def _set_index(self, address: int) -> int:
        return self._line_address(address) % self.config.sets

    def _tag(self, address: int) -> int:
        return self._line_address(address) // self.config.sets

    def _sample_offset(self) -> int:
        if self.config.sampling_mode == "rotating":
            return self._sampling_offset
        return 0

    def _is_sample_set(self, set_index: int) -> bool:
        return (
            set_index % self.config.monitor_group_sets
            == self._sample_offset()
        )

    def _sampling_counter_offset(self, set_index: int) -> int:
        return set_index % self.config.monitor_group_sets

    def _bump_counter(
        self,
        counter: DefaultDict,
        key: object,
        delta: int,
    ) -> None:
        counter[key] += delta
        if counter[key] <= 0:
            counter.pop(key, None)

    def _update_sampled_owner_counters(
        self,
        *,
        set_index: int,
        old_line: CacheLine,
        new_partid: int,
        new_pmg: int,
    ) -> None:
        offset = self._sampling_counter_offset(set_index)
        owner_counter = self._sampled_owner_counters[offset]
        group_counter = self._sampled_group_owner_counters[offset]
        if old_line.valid and old_line.owner_partid is not None:
            self._bump_counter(
                owner_counter,
                old_line.owner_partid,
                -1,
            )
            if old_line.owner_pmg is not None:
                self._bump_counter(
                    group_counter,
                    (old_line.owner_partid, old_line.owner_pmg),
                    -1,
                )
        self._bump_counter(owner_counter, new_partid, 1)
        self._bump_counter(group_counter, (new_partid, new_pmg), 1)

    def _advance_sampling_offset(self) -> None:
        self._monitor_cycle_index += 1
        if self.config.sampling_mode != "rotating":
            self._sampling_offset = 0
            return
        period = self.config.sampling_rotation_period_monitor_cycles
        if self._monitor_cycle_index % period == 0:
            self._sampling_offset = (
                self._sampling_offset + 1
            ) % self.config.monitor_group_sets

    def _eligible_way_indexes(self, partid: int) -> List[int]:
        if not self.enforce_controls:
            return list(range(self.config.ways))
        setting = self.settings.lookup(partid)
        if not setting.cpbm_enable:
            return list(range(self.config.ways))
        bitmap = setting.cache_portion_bitmap
        if bitmap is None:
            return list(range(self.config.ways))
        mask = int(bitmap, 16)
        return [
            index
            for index in range(self.config.ways)
            if mask & (1 << index)
        ]

    @property
    def sampled_capacity_lines(self) -> int:
        sampled_sets = sum(
            1
            for set_index in range(self.config.sets)
            if self._is_sample_set(set_index)
        )
        return sampled_sets * self.config.ways

    def _reachable_percent(self, partid: int) -> float:
        return (
            len(self._eligible_way_indexes(partid))
            * 100.0
            / self.config.ways
        )

    def _effective_min_percent(self, setting: MPAMSetting) -> float:
        if not self.enforce_controls or not setting.cmin_enable:
            return 0.0
        return max(
            0.0,
            min(
                self._reachable_percent(setting.partid),
                setting.cache_min_percent,
            ),
        )

    def _effective_max_percent(self, setting: MPAMSetting) -> float:
        if not self.enforce_controls:
            return 100.0
        reachable = self._reachable_percent(setting.partid)
        configured = (
            setting.cache_max_percent
            if (
                setting.cmax_enable
                and setting.cache_max_percent is not None
            )
            else 100.0
        )
        return max(0.0, min(reachable, configured))

    def _quota_lines(
        self,
        percent: float,
        round_up: bool,
    ) -> int:
        lines = self.sampled_capacity_lines * percent / 100.0
        return (
            math.ceil(lines - 1e-12)
            if round_up
            else math.floor(lines + 1e-12)
        )

    def allowed_capacity_bytes(self, partid: int) -> int:
        percent = self._effective_max_percent(
            self.settings.lookup(partid)
        )
        return int(self.config.size_bytes * percent / 100.0)

    def _owner_counts(
        self,
        sampled_only: bool,
    ) -> Dict[int, int]:
        counts: DefaultDict[int, int] = defaultdict(int)
        for set_index, ways in self._sets.items():
            if sampled_only and not self._is_sample_set(set_index):
                continue
            for line in ways:
                if line.valid and line.owner_partid is not None:
                    counts[line.owner_partid] += 1
        return dict(counts)

    def _sampled_owner_counts(self) -> Dict[int, int]:
        return dict(self._sampled_owner_counters[self._sample_offset()])

    def _control_owner_counts(self) -> Dict[int, float]:
        return dict(self._control_sampled_counts)

    def _actual_owner_counts(self) -> Dict[int, int]:
        return self._owner_counts(sampled_only=False)

    def _sampled_group_owner_counts(
        self,
    ) -> Dict[Tuple[int, int], int]:
        return dict(
            self._sampled_group_owner_counters[self._sample_offset()]
        )

    def _known_monitor_partids(self) -> List[int]:
        return sorted(
            {partid for partid, _ in self.settings.items()}
            | set(self._monitor_sampled_bytes)
            | set(self._sampled_owner_counts())
            | set(self._filtered_sampled_counts)
            | set(self._control_sampled_counts)
            | set(self._cbusy_level_by_partid)
        )

    def _publish_mpam_monitor(self) -> None:
        raw_counts = self._sampled_owner_counts()
        period_ns = self.monitor_period_ns
        weight_sum = (
            self.config.history_weight
            + self.config.current_weight
        )
        sample_scale = self.config.monitor_group_sets
        sample_offset = self._sample_offset()
        self._last_sampling_offset = sample_offset
        local_cycle = int(
            self.kernel.now_ns * self.config.clock_mhz / 1000.0
        )
        for partid in self._known_monitor_partids():
            raw_count = float(raw_counts.get(partid, 0))
            raw_bandwidth = (
                self._monitor_sampled_bytes[partid]
                * sample_scale
                * 8.0
                / period_ns
            )
            previous_bandwidth = (
                self._filtered_sampled_bandwidth_gbps[partid]
            )
            filtered_bandwidth = (
                self.config.history_weight * previous_bandwidth
                + self.config.current_weight * raw_bandwidth
            ) / weight_sum
            self._raw_sampled_counts[partid] = raw_count
            self._filtered_sampled_counts[partid] = raw_count
            self._control_sampled_counts[partid] = raw_count
            self._raw_sampled_bandwidth_gbps[partid] = raw_bandwidth
            self._filtered_sampled_bandwidth_gbps[partid] = (
                filtered_bandwidth
            )
            self._monitor_sampled_bytes[partid] = 0
            self._monitor_updates[partid] += 1
            self._publish_control_state(
                partid,
                local_cycle,
                sample_scale,
                sample_offset,
            )
        self._advance_sampling_offset()
        self.kernel.schedule(
            period_ns,
            self._publish_mpam_monitor,
            f"l3-monitor:{self.component_id}",
        )

    def _publish_control_state(
        self,
        partid: int,
        local_cycle: int,
        sample_scale: int,
        sample_offset: int,
    ) -> None:
        if self.on_control_event is None:
            return
        setting = self.settings.lookup(partid)
        control_count = self._control_sampled_counts[partid]
        cmin_quota = self._quota_lines(
            self._effective_min_percent(setting),
            round_up=True,
        )
        cmax_quota = self._quota_lines(
            self._effective_max_percent(setting),
            round_up=False,
        )
        new_state = {
            "cmin_protected": bool(
                self.enforce_controls
                and setting.cmin_enable
                and cmin_quota > 0
                and control_count > 0
                and control_count <= cmin_quota
            ),
            "cmax_limited": bool(
                self.enforce_controls
                and setting.cmax_enable
                and control_count >= cmax_quota
            ),
        }
        old_state = self._control_state_by_partid.get(
            partid,
            {"cmin_protected": False, "cmax_limited": False},
        )
        self._control_state_by_partid[partid] = dict(new_state)
        if old_state == new_state:
            return
        control_bytes = (
            control_count * sample_scale * self.config.line_size
        )
        monitor_sample_id = (
            f"{self.component_id}:l3_control_input:"
            f"{local_cycle}:partid:{partid}"
        )
        self.on_control_event(
            resource_id=self.component_id,
            partid=partid,
            event_type="limit_state_changed",
            field="l3_cmin_cmax_state",
            old_state=old_state,
            new_state=new_state,
            policy="l3_cmin_cmax",
            reason=(
                "latched sampled-owner control input updates "
                "CMIN/CMAX eligibility"
            ),
            monitor_sample_id=monitor_sample_id,
            decision_id=(
                f"decision:{monitor_sample_id}:l3_cmin_cmax"
            ),
            action_effective_time_ns=self.kernel.now_ns,
            details={
                "local_cycle": local_cycle,
                "control_input_metric": "control_occupancy_bytes",
                "control_input_value": control_bytes,
                "control_input_unit": "byte",
                "control_sampled_way_count": control_count,
                "latest_sampled_way_count": (
                    self._filtered_sampled_counts[partid]
                ),
                "sampling_mode": self.config.sampling_mode,
                "sampling_offset": sample_offset,
                "cmin_quota_lines": cmin_quota,
                "cmax_quota_lines": cmax_quota,
            },
            outcome_state=(
                "saturated"
                if new_state["cmax_limited"]
                else "met"
            ),
            outcome_reason=(
                "CMAX limit active"
                if new_state["cmax_limited"]
                else "L3 limit state updated"
            ),
        )

    def monitor_snapshot(self, interval_ns: float):
        total_requests = sum(
            int(values["requests"])
            for values in self._interval.values()
        )
        total_hits = sum(
            int(values["hits"])
            for values in self._interval.values()
        )
        sampled_counts = self._sampled_owner_counts()
        actual_counts = self._actual_owner_counts()
        group_owner_counts = self._sampled_group_owner_counts()
        configured_partids = {
            partid for partid, _ in self.settings.items()
        }
        partids = sorted(configured_partids | set(self._interval))
        sample_scale = self.config.monitor_group_sets
        per_partid = {}
        for partid in partids:
            values = dict(self._interval[partid])
            setting = self.settings.lookup(partid)
            sampled_bytes = values["sampled_bytes"]
            sampled_count = sampled_counts.get(partid, 0)
            raw_sampled_count = self._raw_sampled_counts[partid]
            filtered_sampled_count = (
                self._filtered_sampled_counts[partid]
            )
            control_sampled_count = self._control_sampled_counts[partid]
            actual_count = actual_counts.get(partid, 0)
            estimated_occupancy = (
                sampled_count
                * sample_scale
                * self.config.line_size
            )
            actual_occupancy = (
                actual_count * self.config.line_size
            )
            raw_occupancy = (
                raw_sampled_count
                * sample_scale
                * self.config.line_size
            )
            filtered_occupancy = (
                filtered_sampled_count
                * sample_scale
                * self.config.line_size
            )
            cmin_percent = self._effective_min_percent(setting)
            cmax_percent = self._effective_max_percent(setting)
            per_partid[str(partid)] = {
                **values,
                "estimated_access_bytes": sampled_bytes * sample_scale,
                "estimated_bandwidth_gbps": (
                    sampled_bytes
                    * sample_scale
                    * 8.0
                    / max(interval_ns, 1e-9)
                ),
                "sampled_way_count": sampled_count,
                "raw_sampled_way_count": raw_sampled_count,
                "filtered_sampled_way_count": filtered_sampled_count,
                "control_sampled_way_count": control_sampled_count,
                "actual_line_count": actual_count,
                "estimated_occupancy_bytes": estimated_occupancy,
                "raw_occupancy_bytes": raw_occupancy,
                "filtered_occupancy_bytes": filtered_occupancy,
                "control_occupancy_bytes": (
                    control_sampled_count
                    * sample_scale
                    * self.config.line_size
                ),
                "actual_occupancy_bytes": actual_occupancy,
                "monitor_error_bytes": (
                    filtered_occupancy - actual_occupancy
                ),
                "monitor_error_percent": (
                    (filtered_occupancy - actual_occupancy)
                    * 100.0
                    / max(1, actual_occupancy)
                ),
                "raw_bandwidth_gbps": (
                    self._raw_sampled_bandwidth_gbps[partid]
                ),
                "filtered_bandwidth_gbps": (
                    self._filtered_sampled_bandwidth_gbps[partid]
                ),
                "monitor_updates": self._monitor_updates[partid],
                "allowed_capacity_bytes": self.allowed_capacity_bytes(partid),
                "cache_capacity_bytes": self.config.size_bytes,
                "occupancy_share": (
                    sampled_count
                    / max(1, self.sampled_capacity_lines)
                ),
                "raw_occupancy_share": (
                    raw_sampled_count
                    / max(1, self.sampled_capacity_lines)
                ),
                "filtered_occupancy_share": (
                    filtered_sampled_count
                    / max(1, self.sampled_capacity_lines)
                ),
                "actual_occupancy_share": (
                    actual_count
                    / max(1, self.config.sets * self.config.ways)
                ),
                "cmin_percent": cmin_percent,
                "cmax_percent": cmax_percent,
                "cmin": cmin_percent,
                "cmax": cmax_percent,
                "cmin_quota_lines": self._quota_lines(
                    cmin_percent,
                    round_up=True,
                ),
                "cmax_quota_lines": self._quota_lines(
                    cmax_percent,
                    round_up=False,
                ),
                "sampled_capacity_lines": self.sampled_capacity_lines,
                "reachable_percent": self._reachable_percent(partid),
                "cpbm": (
                    setting.cache_portion_bitmap
                    if self.enforce_controls and setting.cpbm_enable
                    else f"{(1 << self.config.ways) - 1:x}"
                ),
                "configured_cmin_percent": setting.cache_min_percent,
                "configured_cmax_percent": setting.cache_max_percent,
                "configured_cmin": setting.cache_min_percent,
                "configured_cmax": setting.cache_max_percent,
                "configured_cpbm": setting.cache_portion_bitmap,
                "cmin_enable": (
                    self.enforce_controls and setting.cmin_enable
                ),
                "cmax_enable": (
                    self.enforce_controls and setting.cmax_enable
                ),
                "cpbm_enable": (
                    self.enforce_controls and setting.cpbm_enable
                ),
                "monitor_enable": setting.monitor_enable,
                "enforcement_enabled": self.enforce_controls,
                "cbusy_response_enable": (
                    self._cbusy_response_enabled(partid)
                ),
                "cbusy_level": self._cbusy_level(partid),
                "cbusy_mshr_cap": self._cbusy_mshr_cap(partid),
                "cbusy_mshr_occupancy": (
                    self._partid_mshr_occupancy(partid)
                ),
                "cbusy_mshr_blocks": values["cbusy_mshr_blocks"],
                "cbusy_transitions": (
                    self._cbusy_transitions_by_partid[partid]
                ),
            }

        monitor_groups = {}
        group_keys = sorted(
            set(self._interval_groups) | set(group_owner_counts)
        )
        for partid, pmg in group_keys:
            values = dict(
                self._interval_groups[(partid, pmg)]
            )
            sampled_ways = group_owner_counts.get(
                (partid, pmg),
                0,
            )
            estimated_occupancy = (
                sampled_ways
                * sample_scale
                * self.config.line_size
            )
            allowed_capacity = self.allowed_capacity_bytes(partid)
            monitor_groups[f"{partid}:{pmg}"] = {
                "partid": partid,
                "pmg": pmg,
                **values,
                "estimated_access_bytes": (
                    values["sampled_bytes"] * sample_scale
                ),
                "estimated_bandwidth_gbps": (
                    values["sampled_bytes"]
                    * sample_scale
                    * 8.0
                    / max(interval_ns, 1e-9)
                ),
                "sampled_way_count": sampled_ways,
                "estimated_occupancy_bytes": estimated_occupancy,
                "allowed_capacity_bytes": allowed_capacity,
                "occupancy_rate": min(
                    1.0,
                    estimated_occupancy
                    / max(1.0, allowed_capacity),
                ),
                "occupancy_share": (
                    sampled_ways
                    / max(1, self.sampled_capacity_lines)
                ),
            }

        row = {
            "msc_id": self.component_id,
            "msc_type": "cache",
            "model": "explicit_set_tag_way",
            "replacement_policy": self.config.replacement_policy,
            "merge_same_line_misses": (
                self.config.merge_same_line_misses
            ),
            "utilization": min(
                1.0,
                self._interval_lookup_busy_ns
                / max(
                    interval_ns * self.config.lookup_parallelism,
                    1e-9,
                ),
            ),
            "hit_rate": total_hits / max(1, total_requests),
            "queue_occupancy": (
                self._queue_sample_sum
                / max(1, self._queue_samples)
            ),
            "queue_peak": self._queue_peak,
            "queue_depth": self.config.queue_depth,
            "lookup_parallelism": self.config.lookup_parallelism,
            "active_lookups": self._active_lookups,
            "active_lookup_peak": self._active_peak,
            "mshr_occupancy": self.mshr_occupancy,
            "mshr_peak": self._mshr_peak,
            "mshr_entries": self.config.mshr_entries,
            "mshr_waiting": len(self._mshr_wait_queue),
            "fill_buffer_occupancy": self._fill_buffer_occupancy,
            "fill_buffer_peak": self._fill_buffer_peak,
            "fill_buffer_entries": self.config.fill_buffer_entries,
            "bytes": sum(
                int(values["bytes"])
                for values in self._interval.values()
            ),
            "requests": total_requests,
            "sets": self.config.sets,
            "ways_per_set": self.config.ways,
            "monitor_group_sets": self.config.monitor_group_sets,
            "sampling_mode": self.config.sampling_mode,
            "sampling_offset": self._sample_offset(),
            "last_sampling_offset": self._last_sampling_offset,
            "sampling_rotation_period_monitor_cycles": (
                self.config.sampling_rotation_period_monitor_cycles
            ),
            "clock_mhz": self.config.clock_mhz,
            "monitor_period_cycles": self.config.monitor_period_cycles,
            "monitor_period_ns": self.monitor_period_ns,
            "history_weight": self.config.history_weight,
            "current_weight": self.config.current_weight,
            "cbusy_response_enable": self.config.cbusy_response_enable,
            "instantiated_set_count": len(self._sets),
            "sampled_set_count": sum(
                int(self._is_sample_set(set_index))
                for set_index in self._sets
            ),
            "enforcement_enabled": self.enforce_controls,
            "per_partid": per_partid,
            "monitor_groups": monitor_groups,
        }
        self._interval.clear()
        self._interval_groups.clear()
        self._interval_lookup_busy_ns = 0.0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._queue_peak = len(self._queue)
        self._active_peak = self._active_lookups
        self._mshr_peak = self.mshr_occupancy
        self._fill_buffer_peak = self._fill_buffer_occupancy
        return self.build_monitor_snapshot(
            self.kernel.now_ns,
            interval_ns,
            row,
            local_cycle=int(
                self.kernel.now_ns * self.config.clock_mhz / 1000.0
            ),
        )
