from __future__ import annotations

import heapq
from collections import defaultdict
from typing import Callable, DefaultDict, Dict, List, Tuple

from src.config.schema import NocConfig
from src.sim.component import Component
from src.sim.kernel import SimulationKernel
from src.traffic.request import Request


class NocFabric(Component):
    capabilities = (
        "queued_noc_transport",
        "neutral_request_arbitration",
        "per_partid_monitoring",
    )
    required_monitors = (
        "queue_occupancy",
        "utilization",
        "per_partid_delay",
    )
    actions = ("admit", "backpressure", "forward")
    validation_hooks = ("queue_capacity", "deterministic_order")
    incompatible_capabilities = ("bufferless_ring_transport",)
    approximations = (
        "single queued fabric instead of REQ/RSP/DAT rings",
        "fixed average hop count",
    )

    def __init__(self, kernel: SimulationKernel, config: NocConfig) -> None:
        super().__init__("noc", "noc")
        self.kernel = kernel
        self.config = config
        self._queue: List[Tuple[int, int, Request, Callable[[Request], None]]] = []
        self._sequence = 0
        self._dispatch_scheduled = False
        self._interval_busy_ns = 0.0
        self._interval_requests = 0
        self._interval_bytes = 0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._per_partid: DefaultDict[int, Dict[str, float]] = defaultdict(
            lambda: {"requests": 0, "bytes": 0, "delay_ns": 0.0, "backpressure_ns": 0.0}
        )

    def receive(self, request: Request, downstream: Callable[[Request], None]) -> None:
        if len(self._queue) >= self.config.queue_depth:
            retry_ns = 2.0
            request.noc_delay_ns += retry_ns
            self._per_partid[request.partid]["backpressure_ns"] += retry_ns
            self.kernel.schedule(retry_ns, lambda: self.receive(request, downstream), "noc-backpressure")
            return
        request.noc_enqueue_time_ns = self.kernel.now_ns
        self._sequence += 1
        heapq.heappush(self._queue, (-request.priority, self._sequence, request, downstream))
        self._sample_queue()
        if not self._dispatch_scheduled:
            self._dispatch_scheduled = True
            self.kernel.schedule(0.0, self._dispatch, "noc-dispatch")

    def _dispatch(self) -> None:
        if not self._queue:
            self._dispatch_scheduled = False
            return
        _, _, request, downstream = heapq.heappop(self._queue)
        self._sample_queue()
        serialization_ns = request.size_bytes * 8.0 / self.config.link_bandwidth_gbps
        fixed_latency_ns = self.config.average_hops * self.config.router_latency_ns
        queue_delay_ns = self.kernel.now_ns - request.noc_enqueue_time_ns
        stage_delay_ns = queue_delay_ns + serialization_ns + fixed_latency_ns
        request.noc_delay_ns += stage_delay_ns

        self._interval_busy_ns += serialization_ns
        self._interval_requests += 1
        self._interval_bytes += request.size_bytes
        counters = self._per_partid[request.partid]
        counters["requests"] += 1
        counters["bytes"] += request.size_bytes
        counters["delay_ns"] += stage_delay_ns

        self.kernel.schedule(
            serialization_ns + fixed_latency_ns,
            lambda: downstream(request),
            "noc-arrival",
        )
        self.kernel.schedule(serialization_ns, self._dispatch, "noc-dispatch")

    def _sample_queue(self) -> None:
        self._queue_sample_sum += len(self._queue)
        self._queue_samples += 1

    def monitor_snapshot(self, interval_ns: float):
        utilization = min(1.0, self._interval_busy_ns / max(interval_ns, 1e-9))
        row = {
            "msc_id": self.component_id,
            "msc_type": "noc",
            "utilization": utilization,
            "queue_occupancy": self._queue_sample_sum / max(1, self._queue_samples),
            "bytes": self._interval_bytes,
            "requests": self._interval_requests,
            "per_partid": {str(pid): dict(values) for pid, values in self._per_partid.items()},
        }
        self._interval_busy_ns = 0.0
        self._interval_requests = 0
        self._interval_bytes = 0
        self._queue_sample_sum = 0
        self._queue_samples = 0
        self._per_partid.clear()
        return self.build_monitor_snapshot(
            self.kernel.now_ns,
            interval_ns,
            row,
        )
