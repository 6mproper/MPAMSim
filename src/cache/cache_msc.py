from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, DefaultDict, Dict, List, Optional

from src.config.schema import CacheConfig
from src.mpam.settings import MPAMSetting, SettingsTable
from src.sim.component import Component
from src.sim.kernel import SimulationKernel
from src.traffic.request import Request


@dataclass
class SampleWay:
    owner_partid: Optional[int] = None
    tag: Optional[int] = None
    last_touch: int = 0


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
        self._touch_sequence = 0
        self._sample_sets: Dict[int, List[SampleWay]] = {}
        self._interval: DefaultDict[int, Dict[str, float]] = defaultdict(
            lambda: {
                "requests": 0,
                "hits": 0,
                "misses": 0,
                "bytes": 0,
                "delay_ns": 0.0,
                "sampled_requests": 0,
                "sampled_bytes": 0,
                "allocation_denials": 0,
                "cmin_protected_evictions": 0,
            }
        )

    def receive(self, request: Request) -> None:
        request.cache_id = self.component_id
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

        set_index = self._set_index(request.addr)
        if set_index % self.config.monitor_group_sets == 0:
            counters["sampled_requests"] += 1
            counters["sampled_bytes"] += request.size_bytes
            self._sample_access(request, set_index, is_hit)

        callback = self.on_hit if is_hit else self.on_miss
        self.kernel.schedule(
            self.config.hit_latency_ns,
            lambda: callback(request),
            "cache-result",
        )

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
            return
        ways[victim] = SampleWay(
            owner_partid=request.partid,
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
        current_count = sum(
            way.owner_partid == partid for way in ways
        )
        cmax = self._effective_max_ways(setting)

        empty = [index for index in eligible if ways[index].owner_partid is None]
        if empty and current_count < cmax:
            return empty[0]

        own = [
            index
            for index in eligible
            if ways[index].owner_partid == partid
        ]
        if own:
            return min(own, key=lambda index: ways[index].last_touch)
        if current_count >= cmax:
            return None

        owner_counts: DefaultDict[int, int] = defaultdict(int)
        for way in ways:
            if way.owner_partid is not None:
                owner_counts[way.owner_partid] += 1

        candidates = []
        for index in eligible:
            owner = ways[index].owner_partid
            if owner is None:
                candidates.append(index)
                continue
            owner_cmin = (
                self.settings.lookup(owner).cache_min_ways
                if self.enforce_controls
                else 0
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
        bitmap = self.settings.lookup(partid).cache_portion_bitmap
        if bitmap is None:
            return list(range(self.config.ways))
        mask = int(bitmap, 16)
        return [
            index
            for index in range(self.config.ways)
            if mask & (1 << index)
        ]

    def _effective_max_ways(self, setting: MPAMSetting) -> int:
        if not self.enforce_controls:
            return self.config.ways
        enabled = len(self._eligible_way_indexes(setting.partid))
        configured = (
            setting.cache_max_ways
            if setting.cache_max_ways is not None
            else enabled
        )
        return max(0, min(enabled, configured))

    def allowed_capacity_bytes(self, partid: int) -> int:
        max_ways = self._effective_max_ways(self.settings.lookup(partid))
        return self.config.sets * self.config.line_size * max_ways

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

    def monitor_snapshot(self, interval_ns: float) -> Dict[str, object]:
        total_requests = sum(
            int(values["requests"]) for values in self._interval.values()
        )
        total_hits = sum(
            int(values["hits"]) for values in self._interval.values()
        )
        owner_counts = self._sampled_owner_counts()
        configured_partids = {partid for partid, _ in self.settings.items()}
        partids = sorted(configured_partids | set(self._interval))
        sample_scale = self.config.monitor_group_sets

        per_partid = {}
        for partid in partids:
            values = dict(self._interval[partid])
            setting = self.settings.lookup(partid)
            sampled_bytes = values["sampled_bytes"]
            estimated_bytes = sampled_bytes * sample_scale
            per_partid[str(partid)] = {
                **values,
                "estimated_access_bytes": estimated_bytes,
                "estimated_bandwidth_gbps": (
                    estimated_bytes * 8.0 / max(interval_ns, 1e-9)
                ),
                "sampled_way_count": owner_counts.get(partid, 0),
                "estimated_occupancy_bytes": (
                    owner_counts.get(partid, 0)
                    * sample_scale
                    * self.config.line_size
                ),
                "allowed_capacity_bytes": self.allowed_capacity_bytes(partid),
                "cmin": (
                    setting.cache_min_ways
                    if self.enforce_controls
                    else 0
                ),
                "cmax": self._effective_max_ways(setting),
                "cpbm": (
                    setting.cache_portion_bitmap
                    if self.enforce_controls
                    else f"{(1 << self.config.ways) - 1:x}"
                ),
                "monitor_enable": setting.monitor_enable,
                "enforcement_enabled": self.enforce_controls,
            }

        row = {
            "msc_id": self.component_id,
            "msc_type": "cache",
            "utilization": total_hits / max(1, total_requests),
            "queue_occupancy": 0.0,
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
        }
        self._interval.clear()
        return row
