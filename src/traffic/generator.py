from __future__ import annotations

import math
import random
from typing import Callable

from src.config.schema import WorkloadConfig
from src.sim.kernel import SimulationKernel

from .request import Request
from .requester import RequesterRuntime


class WorkloadGenerator:
    def __init__(
        self,
        kernel: SimulationKernel,
        workload: WorkloadConfig,
        requester: RequesterRuntime,
        requester_count: int,
        seed: int,
        next_request_id: Callable[[], int],
        submit: Callable[[Request], None],
        default_priority: int,
    ) -> None:
        self.kernel = kernel
        self.workload = workload
        self.requester = requester
        self.next_request_id = next_request_id
        self.submit = submit
        self.default_priority = default_priority
        self.rng = random.Random(seed)
        self._stream_addr = 0
        self._interval_ns = self._calculate_interval_ns(max(1, requester_count))
        self._stop_ns = float(workload.stop_ns or 0)
        self._burst_remaining = max(1, workload.burst_length)

    def start(self) -> None:
        jitter = self.rng.random() * min(self._interval_ns, 10.0)
        self.kernel.schedule_at(self.workload.start_ns + jitter, self._issue, f"issue:{self.workload.name}")

    def _calculate_interval_ns(self, requester_count: int) -> float:
        if self.workload.injection_rate_mrps is not None:
            aggregate_requests_per_ns = self.workload.injection_rate_mrps / 1000.0
        else:
            aggregate_requests_per_ns = (
                float(self.workload.injection_rate_gbps) / (self.workload.request_size_bytes * 8.0)
            )
        per_requester_rate = aggregate_requests_per_ns
        if self.workload.rate_scope == "aggregate":
            per_requester_rate /= requester_count
        if per_requester_rate <= 0:
            raise ValueError(f"Workload {self.workload.name} has a non-positive injection rate")
        return 1.0 / per_requester_rate

    def _sample_interval(self) -> float:
        if self.workload.injection_mode == "poisson":
            return max(0.001, self.rng.expovariate(1.0 / self._interval_ns))
        if self.workload.burst_length > 1:
            self._burst_remaining -= 1
            if self._burst_remaining > 0:
                return max(0.001, self._interval_ns / self.workload.burst_length)
            self._burst_remaining = self.workload.burst_length
            return float(self.workload.burst_period_ns or self._interval_ns)
        return self._interval_ns

    def _next_address(self) -> int:
        working_set = max(self.workload.request_size_bytes, self.workload.working_set_bytes)
        distribution = self.workload.address_distribution
        if distribution == "auto":
            distribution = "stream" if self.workload.type == "stream" else "random"
        if distribution == "stream":
            address = self._stream_addr
            self._stream_addr = (self._stream_addr + self.workload.request_size_bytes) % working_set
            return address
        slots = max(1, working_set // self.workload.request_size_bytes)
        return self.rng.randrange(slots) * self.workload.request_size_bytes

    def _issue(self) -> None:
        if self.kernel.now_ns >= self._stop_ns:
            return
        if not self.requester.can_issue(self.workload.partid):
            retry_ns = min(10.0, self._interval_ns)
            self.requester.on_backpressure(
                self.workload.partid,
                retry_ns,
                cbusy=self.requester.blocked_by_cbusy(
                    self.workload.partid
                ),
            )
            self.kernel.schedule(retry_ns, self._issue, f"retry:{self.workload.name}")
            return

        op = "read" if self.rng.random() < self.workload.read_ratio else "write"
        locality = self.workload.locality
        if locality == "auto":
            locality = "low" if self.workload.type in {"pointer_chase", "stream"} else "medium"
        request = Request(
            request_id=self.next_request_id(),
            workload_name=self.workload.name,
            workload_type=self.workload.type,
            requester_id=self.requester.config.id,
            partid=self.workload.partid,
            pmg=self.workload.pmg,
            addr=self._next_address(),
            size_bytes=self.workload.request_size_bytes,
            op=op,
            issue_time_ns=self.kernel.now_ns,
            working_set_bytes=self.workload.working_set_bytes,
            locality=locality,
            source_attach_node=self.requester.config.attach_node,
            priority=self.default_priority,
        )
        self.requester.on_issue(self.workload.partid)
        self.submit(request)
        next_time = self.kernel.now_ns + self._sample_interval()
        if math.isfinite(next_time) and next_time < self._stop_ns:
            self.kernel.schedule_at(next_time, self._issue, f"issue:{self.workload.name}")
