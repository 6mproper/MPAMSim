from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, List, Optional

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
    chain_id: int = 0


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
        self._pending: List[PendingStimulus] = []
        self._chain_count = max(1, int(workload.independent_chains))
        self._chain_waiting: set[int] = set()
        self._chain_next_address = [
            (chain * workload.request_size_bytes)
            % max(workload.request_size_bytes, workload.working_set_bytes)
            for chain in range(self._chain_count)
        ]
        self._next_chain_cursor = 0

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
        if self.workload.arrival_mode == "poisson":
            return max(0.001, self.rng.expovariate(1.0 / self._interval_ns))
        if (
            self.workload.arrival_mode == "burst"
            or self.workload.burst_length > 1
        ):
            self._burst_remaining -= 1
            if self._burst_remaining > 0:
                return max(0.001, self._interval_ns / self.workload.burst_length)
            self._burst_remaining = self.workload.burst_length
            return float(self.workload.burst_period_ns or self._interval_ns)
        return self._interval_ns

    def _pointer_chain_enabled(self) -> bool:
        return self.workload.dependency_mode in {
            "pointer_chain",
            "chained",
        }

    def _address_slots(self) -> int:
        working_set = max(self.workload.request_size_bytes, self.workload.working_set_bytes)
        return max(1, working_set // self.workload.request_size_bytes)

    def _next_address(self, chain_id: int) -> int:
        pattern = self.workload.address_pattern
        if pattern == "auto":
            pattern = self.workload.address_distribution
        if pattern == "auto":
            pattern = "sequential" if self.workload.type == "stream" else "uniform_random"
        if pattern in {"sequential", "stream", "stride"}:
            working_set = max(
                self.workload.request_size_bytes,
                self.workload.working_set_bytes,
            )
            address = self._stream_addr
            self._stream_addr = (self._stream_addr + self.workload.request_size_bytes) % working_set
            return address
        if pattern == "pointer_chase":
            return self._chain_next_address[chain_id]
        slots = self._address_slots()
        if pattern == "hotset":
            slots = max(1, slots // 16)
        return self.rng.randrange(slots) * self.workload.request_size_bytes

    def _successor_address(self, address: int, chain_id: int) -> int:
        slots = self._address_slots()
        current_slot = address // self.workload.request_size_bytes
        mixed = (
            current_slot * 1_103_515_245
            + 12_345
            + chain_id * 2_654_435_761
        ) & 0x7FFF_FFFF
        return (mixed % slots) * self.workload.request_size_bytes

    def _operation(self) -> str:
        if self.workload.operation_mix == "read":
            return "read"
        if self.workload.operation_mix == "write":
            return "write"
        return (
            "read"
            if self.rng.random() < self.workload.read_ratio
            else "write"
        )

    def _locality(self) -> str:
        if self.workload.locality != "auto":
            return self.workload.locality
        return (
            "low"
            if (
                self.workload.type in {"pointer_chase", "stream"}
                or self.workload.address_pattern in {
                    "pointer_chase",
                    "sequential",
                    "stream",
                }
            )
            else "medium"
        )

    def _next_chain_for_generation(self) -> Optional[int]:
        if not self._pointer_chain_enabled():
            return 0
        for offset in range(self._chain_count):
            chain_id = (self._next_chain_cursor + offset) % self._chain_count
            if chain_id in self._chain_waiting:
                continue
            if any(item.chain_id == chain_id for item in self._pending):
                continue
            self._next_chain_cursor = (chain_id + 1) % self._chain_count
            return chain_id
        return None

    def _generate_pending(self) -> bool:
        if len(self._pending) >= self.workload.source_queue_depth:
            return False
        chain_id = self._next_chain_for_generation()
        if chain_id is None:
            return False
        address = self._next_address(chain_id)
        self._pending.append(
            PendingStimulus(
                address=address,
                operation=(
                    "read"
                    if self._pointer_chain_enabled()
                    else self._operation()
                ),
                locality=self._locality(),
                memory_controller_id=self.resolve_destination_mc(
                    address
                ),
                chain_id=chain_id,
            )
        )
        self.requester.on_generated(self.workload.partid)
        return True

    def _issue_candidate_index(self) -> Optional[int]:
        if not self._pending:
            return None
        scan_depth = (
            self.workload.eligible_scan_depth
            if self.workload.issue_selection == "eligible_scan"
            else 1
        )
        for index, pending in enumerate(self._pending[:scan_depth]):
            if self.requester.can_issue(
                self.workload.partid,
                pending.memory_controller_id,
            ):
                return index
        return None

    def _schedule_retry(self, name: str) -> None:
        retry_ns = min(10.0, self._interval_ns)
        self.kernel.schedule(
            retry_ns,
            self._issue,
            f"{name}:{self.workload.name}",
        )

    def _issue(self) -> None:
        if self.kernel.now_ns >= self._stop_ns:
            while self._pending:
                self._pending.pop()
                self.requester.on_pending_cancelled(
                    self.workload.partid
                )
            return

        generated = self._generate_pending()
        pending_index = self._issue_candidate_index()
        if pending_index is None:
            if not self._pending:
                if generated:
                    self._schedule_retry("retry")
                return
            pending = self._pending[0]
            reason = self.requester.last_block_reason(
                self.workload.partid,
                pending.memory_controller_id,
            )
            retry_ns = min(10.0, self._interval_ns)
            self.requester.on_backpressure(
                self.workload.partid,
                pending.memory_controller_id,
                retry_ns,
                reason,
            )
            self._schedule_retry("retry")
            return
        pending = self._pending[pending_index]
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
            self._schedule_retry("ring-retry")
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
            stimulus_chain_id=pending.chain_id,
            priority=self.default_priority,
        )
        request.memory_controller_id = pending.memory_controller_id
        self.requester.on_issue(
            self.workload.partid,
            pending.memory_controller_id,
        )
        if self._pointer_chain_enabled():
            self._chain_waiting.add(pending.chain_id)
        self._pending.pop(pending_index)
        if not self.submit(request):
            raise RuntimeError(
                "REQ Ring admission changed after successful preflight"
            )
        next_time = self.kernel.now_ns + self._sample_interval()
        if math.isfinite(next_time) and next_time < self._stop_ns:
            self.kernel.schedule_at(next_time, self._issue, f"issue:{self.workload.name}")

    def on_complete(self, request: Request) -> None:
        if not self._pointer_chain_enabled():
            return
        chain_id = request.stimulus_chain_id % self._chain_count
        self._chain_waiting.discard(chain_id)
        self._chain_next_address[chain_id] = self._successor_address(
            request.address,
            chain_id,
        )
        if self.kernel.now_ns < self._stop_ns:
            self.kernel.schedule(
                0.0,
                self._issue,
                f"pointer-next:{self.workload.name}",
            )
