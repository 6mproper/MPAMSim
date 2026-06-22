from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable

from src.config.schema import WorkloadConfig
from src.sim.kernel import SimulationKernel

from .request import Request
from .requester import RequesterRuntime


@dataclass(frozen=True)
class PendingStimulus:
    address: int
    operation: str
    locality: str
    memory_controller_id: str


class WorkloadGenerator:
    def __init__(
        self,
        kernel: SimulationKernel,
        workload: WorkloadConfig,
        requester: RequesterRuntime,
        requester_count: int,
        seed: int,
        next_request_id: Callable[[], int],
        submit: Callable[[Request], bool],
        can_submit: Callable[[], bool],
        on_submit_backpressure: Callable[[int, float], None],
        resolve_destination_mc: Callable[[int], str],
        default_priority: int,
    ) -> None:
        self.kernel = kernel
        self.workload = workload
        self.requester = requester
        self.next_request_id = next_request_id
        self.submit = submit
        self.can_submit = can_submit
        self.on_submit_backpressure = on_submit_backpressure
        self.resolve_destination_mc = resolve_destination_mc
        self.default_priority = default_priority
        self.rng = random.Random(seed)
        self._stream_addr = 0
        self._interval_ns = self._calculate_interval_ns(max(1, requester_count))
        self._stop_ns = float(workload.stop_ns or 0)
        self._burst_remaining = max(1, workload.burst_length)
        self._pending: PendingStimulus | None = None
        self._source_queue: list[PendingStimulus] = []

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
            if self._pending is not None:
                self.requester.on_pending_cancelled(
                    self.workload.partid
                )
                self._pending = None
            return
        if self.workload.dependency_mode == "pointer_chain":
            outstanding = self.requester.outstanding_by_partid.get(self.workload.partid, 0)
            if outstanding > 0:
                retry_ns = min(10.0, self._interval_ns)
                self.kernel.schedule(retry_ns, self._issue, f"chain-wait:{self.workload.name}")
                return
        if self._pending is None:
            op = (
                "read"
                if self.rng.random() < self.workload.read_ratio
                else "write"
            )
            locality = self.workload.locality
            if locality == "auto":
                locality = (
                    "low"
                    if self.workload.type in {"pointer_chase", "stream"}
                    else "medium"
                )
            address = self._next_address()
            self._pending = PendingStimulus(
                address=address,
                operation=op,
                locality=locality,
                memory_controller_id=self.resolve_destination_mc(
                    address
                ),
            )
            self.requester.on_generated(self.workload.partid)

        pending = self._pending
        if not self.requester.can_issue(
            self.workload.partid,
            pending.memory_controller_id,
        ):
            retry_ns = min(10.0, self._interval_ns)
            reason = self.requester.last_block_reason(
                self.workload.partid,
                pending.memory_controller_id,
            )
            self.requester.on_backpressure(
                self.workload.partid,
                pending.memory_controller_id,
                retry_ns,
                reason,
            )
            self.kernel.schedule(
                retry_ns,
                self._issue,
                f"retry:{self.workload.name}",
            )
            return
        if not self.can_submit():
            retry_ns = min(
                max(0.001, self._interval_ns),
                10.0,
            )
            self.requester.on_backpressure(
                self.workload.partid,
                pending.memory_controller_id,
                retry_ns,
                "req_ring",
            )
            self.on_submit_backpressure(
                self.workload.partid,
                retry_ns,
            )
            self.kernel.schedule(
                retry_ns,
                self._issue,
                f"ring-retry:{self.workload.name}",
            )
            return

        request = Request(
            transaction_id=self.next_request_id(),
            workload_name=self.workload.name,
            workload_type=self.workload.type,
            requester_id=self.requester.config.id,
            partid=self.workload.partid,
            pmg=self.workload.pmg,
            address=pending.address,
            size_bytes=self.workload.request_size_bytes,
            operation=pending.operation,
            issue_time_ns=self.kernel.now_ns,
            working_set_bytes=self.workload.working_set_bytes,
            locality=pending.locality,
            source_node=self.requester.config.attach_node,
            core_id=self.requester.config.core or "",
            thread_id=int(self.requester.config.thread or 0),
            priority=self.default_priority,
        )
        request.memory_controller_id = pending.memory_controller_id
        self.requester.on_issue(
            self.workload.partid,
            pending.memory_controller_id,
        )
        self._pending = None
        if not self.submit(request):
            raise RuntimeError(
                "REQ Ring admission changed after successful preflight"
            )
        next_time = self.kernel.now_ns + self._sample_interval()
        if math.isfinite(next_time) and next_time < self._stop_ns:
            self.kernel.schedule_at(next_time, self._issue, f"issue:{self.workload.name}")
