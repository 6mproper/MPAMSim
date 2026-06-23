from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Dict, Iterable, List

from src.contracts.telemetry import (
    ControlEvent,
    MonitorSample,
    MonitorSnapshot,
)
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
        self.noc_delay_ns += (
            request.timing.req_ring_delay_ns
            + request.timing.rsp_dat_ring_delay_ns
        )
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
        self.requester_mc_rows: List[Dict[str, object]] = []
        self.timeline_rows: List[Dict[str, object]] = []
        self.control_rows: List[Dict[str, object]] = []
        self.monitor_sample_rows: List[Dict[str, object]] = []
        self.monitor_snapshots: List[MonitorSnapshot] = []
        self.control_events: List[ControlEvent] = []
        self._monitor_sample_ids: set[str] = set()
        self.last_interval_metrics: Dict[int, Dict[str, float]] = {}
        self.last_capture_ns = 0.0
        self.last_capture_id = ""

    def on_complete(self, request: Request, completion_time_ns: float) -> None:
        request.mark_complete(completion_time_ns)
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
                        "core_id": request.core_id,
                        "thread_id": request.thread_id,
                        "stimulus_chain_id": request.stimulus_chain_id,
                        "operation": request.operation.value,
                        "request_class": request.request_class.value,
                        "line_address": request.line_address,
                        "completion_condition": (
                            request.completion_condition.value
                        ),
                        "cache_id": request.cache_id,
                        "memory_controller_id": request.memory_controller_id,
                        "cache_hit": request.cache_hit,
                        "mc_base_qos": (
                            request.mc_arbitration.base_qos
                        ),
                        "mc_effective_qos": (
                            request.mc_arbitration.effective_qos
                        ),
                        "mc_aging_steps": (
                            request.mc_arbitration.aging_steps
                        ),
                        "mc_bmin_promoted": (
                            request.mc_arbitration.bmin_promoted
                        ),
                        "mc_soft_demoted": (
                            request.mc_arbitration.soft_demoted
                        ),
                        "return_cbusy_source": (
                            request.return_cbusy_source
                        ),
                        "return_cbusy_level": (
                            request.return_cbusy_level
                        ),
                        "return_cbusy_ostd_cap": (
                            request.return_cbusy_ostd_cap
                        ),
                        "return_cbusy_sample_time_ns": (
                            request.return_cbusy_sample_time_ns
                        ),
                        "noc_delay_ns": request.noc_delay_ns,
                        "req_ring_delay_ns": (
                            request.timing.req_ring_delay_ns
                        ),
                        "rsp_dat_ring_delay_ns": (
                            request.timing.rsp_dat_ring_delay_ns
                        ),
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
        capture_id: str = "",
    ) -> Dict[int, Dict[str, float]]:
        elapsed = max(1.0, time_ns - self.last_capture_ns)
        self.last_capture_id = capture_id or f"interval:{time_ns:g}"
        current: Dict[int, Dict[str, float]] = {}
        for partid, stats in sorted(self.interval.items()):
            metrics = stats.as_metrics(elapsed)
            current[partid] = metrics
            self.metrics_rows.append({"time_ns": time_ns, "partid": partid, **metrics})

        policy_snapshot = MonitorSnapshot.from_payload(
            time_ns=time_ns,
            resource_type="system_metrics",
            resource_id="collector",
            interval_ns=elapsed,
            sample_id=self.last_capture_id,
            payload={
                "per_partid": {
                    str(partid): metrics
                    for partid, metrics in current.items()
                }
            },
        )
        self.monitor_snapshots.append(policy_snapshot)
        self.monitor_sample_rows.extend(
            sample.to_row() for sample in policy_snapshot.samples
        )
        self._monitor_sample_ids.update(
            sample.sample_id for sample in policy_snapshot.samples
        )

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
            for row in requester.capture_partid_mc_rows():
                self.requester_mc_rows.append(
                    {"time_ns": time_ns, **row}
                )
        for core_pool in {
            id(requester.core_pool): requester.core_pool
            for requester in requester_runtimes
        }.values():
            core_pool.reset_interval_peak()
        for component in components:
            snapshot = component.monitor_snapshot(elapsed)
            self.monitor_snapshots.append(snapshot)
            self.monitor_sample_rows.extend(
                sample.to_row() for sample in snapshot.samples
            )
            self._monitor_sample_ids.update(
                sample.sample_id for sample in snapshot.samples
            )
            self.msc_rows.append(
                {
                    "time_ns": time_ns,
                    **snapshot.to_row(),
                    "sample_id": snapshot.sample_id,
                    "capture_id": self.last_capture_id,
                    "requesters": requester_rows,
                }
            )

        self.interval.clear()
        self.last_interval_metrics = current
        self.last_capture_ns = time_ns
        return current

    def record_control(self, event: ControlEvent) -> None:
        self.control_events.append(event)
        self.control_rows.append(event.to_row())

    def record_monitor_sample(self, sample: MonitorSample) -> None:
        if sample.sample_id in self._monitor_sample_ids:
            return
        self._monitor_sample_ids.add(sample.sample_id)
        self.monitor_sample_rows.append(sample.to_row())

    def cumulative_metrics(self, elapsed_ns: float) -> Dict[int, Dict[str, float]]:
        return {
            partid: stats.as_metrics(elapsed_ns)
            for partid, stats in sorted(self.cumulative.items())
        }
