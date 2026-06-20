from __future__ import annotations

import math
import random
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, DefaultDict, Deque, Dict, List, Optional, Tuple

from src.config.schema import CacheConfig
from src.mpam.settings import MPAMSetting, SettingsTable
from src.sim.component import Component
from src.sim.kernel import SimulationKernel
from src.traffic.request import Request


@dataclass
class SampleWay:
    owner_partid: Optional[int] = None
    owner_pmg: Optional[int] = None
    tag: Optional[int] = None
    last_touch: int = 0


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
        "cmin_protected_evictions": 0,
        "queue_delay_ns": 0.0,
        "admission_backpressure_ns": 0.0,
        "queue_full_events": 0,
    }


class CacheMSC(Component):
    def __init__(
        self,
        kernel: SimulationKernel,
        config: CacheConfig,
        settings: SettingsTable,
        seed: int,
        on_hit: Callable[[Request], None],
        on_miss: Callable[[Request], None],
        enforce_controls: bool = True,
    ) -> None:
        super().__init__(config.id)
        self.kernel = kernel
        self.config = config
        self.settings = settings
        self.rng = random.Random(seed)
        self.on_hit = on_hit
        self.on_miss = on_miss
        self.enforce_controls = enforce_controls
        self._queue: Deque[Request] = deque()
        self._active_lookups = 0
        self._interval_lookup_busy_ns = 0.0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._queue_peak = 0
        self._active_peak = 0
        self._touch_sequence = 0
        self._sample_sets: Dict[int, List[SampleWay]] = {}
        self._interval: DefaultDict[int, Dict[str, float]] = defaultdict(
            _cache_counters
        )
        self._interval_groups: DefaultDict[
            Tuple[int, int], Dict[str, float]
        ] = defaultdict(
            _cache_counters
        )

    def receive(self, request: Request) -> None:
        request.cache_id = self.component_id
        if len(self._queue) >= self.config.queue_depth:
            retry_ns = 2.0
            request.cache_queue_delay_ns += retry_ns
            request.cache_delay_ns += retry_ns
            counters = self._interval[request.partid]
            counters["admission_backpressure_ns"] += retry_ns
            counters["queue_full_events"] += 1
            group_counters = self._interval_groups[
                (request.partid, request.pmg)
            ]
            group_counters["admission_backpressure_ns"] += retry_ns
            group_counters["queue_full_events"] += 1
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
            self._interval[request.partid][
                "queue_delay_ns"
            ] += queue_delay
            self._interval_groups[
                (request.partid, request.pmg)
            ]["queue_delay_ns"] += queue_delay
            self._active_lookups += 1
            self._active_peak = max(
                self._active_peak,
                self._active_lookups,
            )
            self._sample_queue()
            self._start_lookup(request)

    def _start_lookup(self, request: Request) -> None:
        allowed_capacity = self.allowed_capacity_bytes(request.partid)
        hit_probability = self._hit_probability(request, allowed_capacity)
        is_hit = self.rng.random() < hit_probability
        request.cache_hit = is_hit
        request.cache_delay_ns += self.config.hit_latency_ns

        counters = self._interval[request.partid]
        counters["requests"] += 1
        counters["bytes"] += request.size_bytes
        counters["delay_ns"] += self.config.hit_latency_ns
        counters["hits" if is_hit else "misses"] += 1
        group_counters = self._interval_groups[
            (request.partid, request.pmg)
        ]
        group_counters["requests"] += 1
        group_counters["bytes"] += request.size_bytes
        group_counters["delay_ns"] += self.config.hit_latency_ns
        group_counters["hits" if is_hit else "misses"] += 1

        set_index = self._set_index(request.addr)
        if set_index % self.config.monitor_group_sets == 0:
            counters["sampled_requests"] += 1
            counters["sampled_bytes"] += request.size_bytes
            group_counters["sampled_requests"] += 1
            group_counters["sampled_bytes"] += request.size_bytes
            self._sample_access(request, set_index, is_hit)

        callback = self.on_hit if is_hit else self.on_miss
        self._interval_lookup_busy_ns += self.config.hit_latency_ns
        self.kernel.schedule(
            self.config.hit_latency_ns,
            lambda: self._finish_lookup(request, callback),
            "cache-result",
        )

    def _finish_lookup(
        self,
        request: Request,
        callback: Callable[[Request], None],
    ) -> None:
        self._active_lookups = max(0, self._active_lookups - 1)
        callback(request)
        self._sample_queue()
        self._dispatch()

    def _sample_queue(self) -> None:
        self._queue_sample_sum += len(self._queue)
        self._queue_samples += 1
        self._queue_peak = max(self._queue_peak, len(self._queue))

    def _set_index(self, address: int) -> int:
        return (address // self.config.line_size) % self.config.sets

    def _tag(self, address: int) -> int:
        return address // (self.config.line_size * self.config.sets)

    def _sample_access(
        self,
        request: Request,
        set_index: int,
        probabilistic_hit: bool,
    ) -> None:
        group_index = set_index // self.config.monitor_group_sets
        ways = self._sample_sets.setdefault(
            group_index,
            [SampleWay() for _ in range(self.config.ways)],
        )
        tag = self._tag(request.addr)
        eligible = self._eligible_way_indexes(request.partid)
        self._touch_sequence += 1

        matching = next(
            (
                index
                for index in eligible
                if ways[index].owner_partid == request.partid
                and ways[index].tag == tag
            ),
            None,
        )
        if matching is not None:
            ways[matching].last_touch = self._touch_sequence
            return
        if probabilistic_hit:
            return

        victim = self._choose_victim(ways, request.partid, eligible)
        if victim is None:
            self._interval[request.partid]["allocation_denials"] += 1
            self._interval_groups[
                (request.partid, request.pmg)
            ]["allocation_denials"] += 1
            return
        ways[victim] = SampleWay(
            owner_partid=request.partid,
            owner_pmg=request.pmg,
            tag=tag,
            last_touch=self._touch_sequence,
        )

    def _choose_victim(
        self,
        ways: List[SampleWay],
        partid: int,
        eligible: List[int],
    ) -> Optional[int]:
        setting = self.settings.lookup(partid)
        owner_counts = self._sampled_owner_counts()
        current_count = owner_counts.get(partid, 0)
        cmax = self._quota_lines(
            self._effective_max_percent(setting),
            round_up=False,
        )

        if current_count >= cmax:
            own = [
                index
                for index in eligible
                if ways[index].owner_partid == partid
            ]
            return (
                min(own, key=lambda index: ways[index].last_touch)
                if own
                else None
            )

        empty = [
            index
            for index in eligible
            if ways[index].owner_partid is None
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
            if owner_counts[owner] > owner_cmin:
                candidates.append(index)
            else:
                self._interval[partid]["cmin_protected_evictions"] += 1
        if not candidates:
            return None
        return min(candidates, key=lambda index: ways[index].last_touch)

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
        sampled_sets = math.ceil(
            self.config.sets / self.config.monitor_group_sets
        )
        return sampled_sets * self.config.ways

    def _reachable_percent(self, partid: int) -> float:
        return (
            len(self._eligible_way_indexes(partid))
            * 100.0
            / self.config.ways
        )

    def _effective_min_percent(self, setting: MPAMSetting) -> float:
        if not self.enforce_controls:
            return 0.0
        if not setting.cmin_enable:
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
        return int(
            self.config.size_bytes * percent / 100.0
        )

    def _hit_probability(
        self,
        request: Request,
        allowed_capacity: int,
    ) -> float:
        if allowed_capacity <= 0:
            return 0.0
        fit = min(
            1.0,
            allowed_capacity
            / max(1.0, float(request.working_set_bytes)),
        )
        locality_weight = {
            "low": 0.45,
            "medium": 0.75,
            "high": 0.95,
        }.get(request.locality, 0.65)
        if request.workload_type == "stream":
            locality_weight *= 0.35
        elif request.workload_type == "pointer_chase":
            locality_weight *= 0.65
        return min(0.98, 0.01 + locality_weight * fit)

    def _sampled_owner_counts(self) -> Dict[int, int]:
        counts: DefaultDict[int, int] = defaultdict(int)
        for ways in self._sample_sets.values():
            for way in ways:
                if way.owner_partid is not None:
                    counts[way.owner_partid] += 1
        return dict(counts)

    def _sampled_group_owner_counts(
        self,
    ) -> Dict[Tuple[int, int], int]:
        counts: DefaultDict[Tuple[int, int], int] = defaultdict(int)
        for ways in self._sample_sets.values():
            for way in ways:
                if (
                    way.owner_partid is not None
                    and way.owner_pmg is not None
                ):
                    counts[
                        (way.owner_partid, way.owner_pmg)
                    ] += 1
        return dict(counts)

    def monitor_snapshot(self, interval_ns: float) -> Dict[str, object]:
        total_requests = sum(
            int(values["requests"]) for values in self._interval.values()
        )
        total_hits = sum(
            int(values["hits"]) for values in self._interval.values()
        )
        owner_counts = self._sampled_owner_counts()
        group_owner_counts = self._sampled_group_owner_counts()
        configured_partids = {partid for partid, _ in self.settings.items()}
        partids = sorted(configured_partids | set(self._interval))
        sample_scale = self.config.monitor_group_sets

        per_partid = {}
        for partid in partids:
            values = dict(self._interval[partid])
            setting = self.settings.lookup(partid)
            sampled_bytes = values["sampled_bytes"]
            estimated_bytes = sampled_bytes * sample_scale
            sampled_count = owner_counts.get(partid, 0)
            occupancy_share = (
                sampled_count / max(1, self.sampled_capacity_lines)
            )
            cmin_percent = self._effective_min_percent(setting)
            cmax_percent = self._effective_max_percent(setting)
            per_partid[str(partid)] = {
                **values,
                "estimated_access_bytes": estimated_bytes,
                "estimated_bandwidth_gbps": (
                    estimated_bytes * 8.0 / max(interval_ns, 1e-9)
                ),
                "sampled_way_count": sampled_count,
                "estimated_occupancy_bytes": (
                    sampled_count
                    * sample_scale
                    * self.config.line_size
                ),
                "allowed_capacity_bytes": self.allowed_capacity_bytes(partid),
                "cache_capacity_bytes": self.config.size_bytes,
                "occupancy_share": occupancy_share,
                "cmin_percent": cmin_percent,
                "cmax_percent": cmax_percent,
                "cmin": cmin_percent,
                "cmax": cmax_percent,
                "cmin_quota_lines": self._quota_lines(
                    cmin_percent, round_up=True
                ),
                "cmax_quota_lines": self._quota_lines(
                    cmax_percent, round_up=False
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
                "cmin_enable": self.enforce_controls and setting.cmin_enable,
                "cmax_enable": self.enforce_controls and setting.cmax_enable,
                "cpbm_enable": self.enforce_controls and setting.cpbm_enable,
                "monitor_enable": setting.monitor_enable,
                "enforcement_enabled": self.enforce_controls,
            }

        monitor_groups = {}
        group_keys = sorted(
            set(self._interval_groups) | set(group_owner_counts)
        )
        for partid, pmg in group_keys:
            values = dict(self._interval_groups[(partid, pmg)])
            sampled_bytes = values["sampled_bytes"]
            estimated_access_bytes = sampled_bytes * sample_scale
            sampled_ways = group_owner_counts.get((partid, pmg), 0)
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
                "estimated_access_bytes": estimated_access_bytes,
                "estimated_bandwidth_gbps": (
                    estimated_access_bytes
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
            "bytes": sum(
                int(values["bytes"]) for values in self._interval.values()
            ),
            "requests": total_requests,
            "sets": self.config.sets,
            "ways_per_set": self.config.ways,
            "monitor_group_sets": self.config.monitor_group_sets,
            "sampled_set_count": len(self._sample_sets),
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
        return row
