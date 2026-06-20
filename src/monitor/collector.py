from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, Iterable, List

from src.sim.component import Component
from src.traffic.request import Request
from src.traffic.requester import RequesterRuntime

from .metrics import percentile


@dataclass
class PartidStats:
    requests: int = 0
    bytes: int = 0
    latencies: List[float] = field(default_factory=list)
    noc_delay_ns: float = 0.0
    cache_delay_ns: float = 0.0
    cache_queue_delay_ns: float = 0.0
    mem_queue_delay_ns: float = 0.0
    mem_service_delay_ns: float = 0.0
    throttle_delay_ns: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0

    def add(self, request: Request, completion_time_ns: float) -> None:
        latency = completion_time_ns - request.issue_time_ns
        self.requests += 1
        self.bytes += request.size_bytes
        self.latencies.append(latency)
        self.noc_delay_ns += request.noc_delay_ns
        self.cache_delay_ns += request.cache_delay_ns
        self.cache_queue_delay_ns += request.cache_queue_delay_ns
        self.mem_queue_delay_ns += request.mem_queue_delay_ns
        self.mem_service_delay_ns += request.mem_service_delay_ns
        self.throttle_delay_ns += request.throttle_delay_ns
        self.cache_hits += int(request.cache_hit)
        self.cache_misses += int(not request.cache_hit)

    def as_metrics(self, elapsed_ns: float) -> Dict[str, float]:
        count = max(1, self.requests)
        return {
            "requests": self.requests,
            "bytes": self.bytes,
            "throughput_gbps": self.bytes * 8.0 / max(elapsed_ns, 1e-9),
            "avg_latency_ns": sum(self.latencies) / count if self.latencies else 0.0,
            "p50_latency_ns": percentile(self.latencies, 50),
            "p95_latency_ns": percentile(self.latencies, 95),
            "p99_latency_ns": percentile(self.latencies, 99),
            "p999_latency_ns": percentile(self.latencies, 99.9),
            "max_latency_ns": max(self.latencies) if self.latencies else 0.0,
            "avg_noc_delay_ns": self.noc_delay_ns / count,
            "avg_cache_delay_ns": self.cache_delay_ns / count,
            "avg_cache_queue_delay_ns": self.cache_queue_delay_ns / count,
            "avg_mem_queue_delay_ns": self.mem_queue_delay_ns / count,
            "avg_mem_service_delay_ns": self.mem_service_delay_ns / count,
            "avg_throttle_delay_ns": self.throttle_delay_ns / count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / max(1, self.cache_hits + self.cache_misses),
        }


class MetricsCollector:
    def __init__(self, trace_requests: bool = False) -> None:
        self.trace_requests = trace_requests
        self.total_completed = 0
        self.cumulative: DefaultDict[int, PartidStats] = defaultdict(PartidStats)
        self.interval: DefaultDict[int, PartidStats] = defaultdict(PartidStats)
        self.metrics_rows: List[Dict[str, object]] = []
        self.msc_rows: List[Dict[str, object]] = []
        self.requester_rows: List[Dict[str, object]] = []
        self.timeline_rows: List[Dict[str, object]] = []
        self.control_rows: List[Dict[str, object]] = []
        self.last_interval_metrics: Dict[int, Dict[str, float]] = {}
        self.last_capture_ns = 0.0

    def on_complete(self, request: Request, completion_time_ns: float) -> None:
        self.total_completed += 1
        self.cumulative[request.partid].add(request, completion_time_ns)
        self.interval[request.partid].add(request, completion_time_ns)
        if self.trace_requests or self.total_completed <= 1000 or self.total_completed % 100 == 0:
            if len(self.timeline_rows) < 20_000:
                self.timeline_rows.append(
                    {
                        "time_ns": completion_time_ns,
                        "request_id": request.request_id,
                        "partid": request.partid,
                        "pmg": request.pmg,
                        "requester_id": request.requester_id,
                        "cache_id": request.cache_id,
                        "memory_controller_id": request.memory_controller_id,
                        "cache_hit": request.cache_hit,
                        "noc_delay_ns": request.noc_delay_ns,
                        "cache_delay_ns": request.cache_delay_ns,
                        "cache_queue_delay_ns": request.cache_queue_delay_ns,
                        "mem_queue_delay_ns": request.mem_queue_delay_ns,
                        "mem_service_delay_ns": request.mem_service_delay_ns,
                        "throttle_delay_ns": request.throttle_delay_ns,
                        "total_latency_ns": completion_time_ns - request.issue_time_ns,
                    }
                )

    def capture_interval(
        self,
        time_ns: float,
        components: Iterable[Component],
        requesters: Iterable[RequesterRuntime],
    ) -> Dict[int, Dict[str, float]]:
        elapsed = max(1.0, time_ns - self.last_capture_ns)
        current: Dict[int, Dict[str, float]] = {}
        for partid, stats in sorted(self.interval.items()):
            metrics = stats.as_metrics(elapsed)
            current[partid] = metrics
            self.metrics_rows.append({"time_ns": time_ns, "partid": partid, **metrics})

        requester_runtimes = list(requesters)
        requester_rows = {
            requester.config.id: {
                "issued": requester.issued,
                "completed": requester.completed,
                "outstanding": requester.outstanding,
                "backpressure_ns": requester.backpressure_ns,
            }
            for requester in requester_runtimes
        }
        for requester in requester_runtimes:
            for row in requester.capture_partid_rows():
                self.requester_rows.append(
                    {"time_ns": time_ns, **row}
                )
        for component in components:
            snapshot = component.monitor_snapshot(elapsed)
            self.msc_rows.append({"time_ns": time_ns, **snapshot, "requesters": requester_rows})

        self.interval.clear()
        self.last_interval_metrics = current
        self.last_capture_ns = time_ns
        return current

    def record_control(
        self,
        time_ns: float,
        policy: str,
        target_msc: str,
        partid: int,
        field: str,
        old_value: object,
        new_value: object,
        reason: str,
    ) -> None:
        self.control_rows.append(
            {
                "time_ns": time_ns,
                "policy": policy,
                "target_msc": target_msc,
                "partid": partid,
                "field": field,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason,
            }
        )

    def cumulative_metrics(self, elapsed_ns: float) -> Dict[int, Dict[str, float]]:
        return {
            partid: stats.as_metrics(elapsed_ns)
            for partid, stats in sorted(self.cumulative.items())
        }
