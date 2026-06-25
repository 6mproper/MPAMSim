from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from src.config.schema import RequesterConfig


@dataclass
class CoreOstdPool:
    core_id: str
    max_outstanding: int
    policy: str
    thread_reserve: int
    thread_limits: Dict[str, int]
    outstanding: int = 0
    peak_outstanding: int = 0
    outstanding_by_thread: Dict[str, int] = field(default_factory=dict)
    outstanding_by_partid: Dict[int, int] = field(default_factory=dict)
    peak_outstanding_by_partid: Dict[int, int] = field(
        default_factory=dict
    )
    outstanding_by_partid_mc: Dict[Tuple[int, str], int] = field(
        default_factory=dict
    )
    peak_outstanding_by_partid_mc: Dict[Tuple[int, str], int] = field(
        default_factory=dict
    )
    pending_threads: Set[str] = field(default_factory=set)
    last_granted_thread: str = ""

    def __post_init__(self) -> None:
        for thread_id in self.thread_limits:
            self.outstanding_by_thread.setdefault(thread_id, 0)

    @property
    def thread_ids(self) -> Tuple[str, ...]:
        return tuple(sorted(self.thread_limits))

    def mark_pending(self, thread_id: str, pending: bool) -> None:
        if pending:
            self.pending_threads.add(thread_id)
        else:
            self.pending_threads.discard(thread_id)

    def _static_limit(self, thread_id: str) -> int:
        threads = self.thread_ids
        if not threads:
            return self.max_outstanding
        base = self.max_outstanding // len(threads)
        remainder = self.max_outstanding % len(threads)
        index = threads.index(thread_id)
        return max(1, base + int(index < remainder))

    def _policy_allows(self, thread_id: str) -> bool:
        current = self.outstanding_by_thread.get(thread_id, 0)
        thread_limit = self.thread_limits[thread_id]
        if current >= thread_limit or self.outstanding >= self.max_outstanding:
            return False
        if self.policy == "static_partition":
            return current < min(
                thread_limit,
                self._static_limit(thread_id),
            )
        if self.policy == "reserve_borrow":
            reserve = min(self.thread_reserve, thread_limit)
            if current < reserve:
                return True
            unused_other_reserve = sum(
                max(
                    0,
                    min(
                        self.thread_reserve,
                        self.thread_limits[other],
                    )
                    - self.outstanding_by_thread.get(other, 0),
                )
                for other in self.thread_ids
                if other != thread_id
            )
            return (
                self.outstanding + 1
                <= self.max_outstanding - unused_other_reserve
            )
        return True

    def _eligible_pending(self) -> Tuple[str, ...]:
        return tuple(
            thread_id
            for thread_id in self.thread_ids
            if (
                thread_id in self.pending_threads
                and self._policy_allows(thread_id)
            )
        )

    def _round_robin_turn(self) -> Optional[str]:
        eligible = self._eligible_pending()
        if not eligible:
            return None
        if self.last_granted_thread not in self.thread_ids:
            return eligible[0]
        start = (
            self.thread_ids.index(self.last_granted_thread) + 1
        )
        for offset in range(len(self.thread_ids)):
            candidate = self.thread_ids[
                (start + offset) % len(self.thread_ids)
            ]
            if candidate in eligible:
                return candidate
        return eligible[0]

    def block_reason(self, thread_id: str) -> Optional[str]:
        if not self._policy_allows(thread_id):
            return "core_ostd"
        turn = self._round_robin_turn()
        if turn is not None and turn != thread_id:
            return "core_round_robin"
        return None

    def allocate(
        self,
        thread_id: str,
        partid: Optional[int] = None,
        mc_id: str = "",
        remains_pending: bool = False,
    ) -> None:
        reason = self.block_reason(thread_id)
        if reason is not None:
            raise RuntimeError(
                f"Core OSTD allocation without admission: {reason}"
            )
        self.outstanding += 1
        self.outstanding_by_thread[thread_id] = (
            self.outstanding_by_thread.get(thread_id, 0) + 1
        )
        if partid is not None:
            self.outstanding_by_partid[partid] = (
                self.outstanding_by_partid.get(partid, 0) + 1
            )
            self.peak_outstanding_by_partid[partid] = max(
                self.peak_outstanding_by_partid.get(partid, 0),
                self.outstanding_by_partid[partid],
            )
            key = (partid, mc_id)
            self.outstanding_by_partid_mc[key] = (
                self.outstanding_by_partid_mc.get(key, 0) + 1
            )
            self.peak_outstanding_by_partid_mc[key] = max(
                self.peak_outstanding_by_partid_mc.get(key, 0),
                self.outstanding_by_partid_mc[key],
            )
        self.peak_outstanding = max(
            self.peak_outstanding,
            self.outstanding,
        )
        self.last_granted_thread = thread_id
        self.mark_pending(thread_id, remains_pending)

    def release(
        self,
        thread_id: str,
        partid: Optional[int] = None,
        mc_id: str = "",
    ) -> None:
        self.outstanding = max(0, self.outstanding - 1)
        self.outstanding_by_thread[thread_id] = max(
            0,
            self.outstanding_by_thread.get(thread_id, 0) - 1,
        )
        if partid is not None:
            self.outstanding_by_partid[partid] = max(
                0,
                self.outstanding_by_partid.get(partid, 0) - 1,
            )
            key = (partid, mc_id)
            self.outstanding_by_partid_mc[key] = max(
                0,
                self.outstanding_by_partid_mc.get(key, 0) - 1,
            )

    def partid_mc_outstanding(self, partid: int, mc_id: str) -> int:
        return self.outstanding_by_partid_mc.get((partid, mc_id), 0)

    def status(
        self,
        partid: Optional[int] = None,
        mc_id: str = "",
    ) -> Dict[str, object]:
        result = {
            "core_id": self.core_id,
            "core_ostd": self.outstanding,
            "core_ostd_peak": self.peak_outstanding,
            "core_ostd_limit": self.max_outstanding,
            "core_ostd_policy": self.policy,
            "thread_ostd_reserve": self.thread_reserve,
        }
        if partid is not None:
            result.update(
                {
                    "core_partid_ostd": (
                        self.outstanding_by_partid.get(partid, 0)
                    ),
                    "core_partid_ostd_peak": (
                        self.peak_outstanding_by_partid.get(partid, 0)
                    ),
                }
            )
            if mc_id:
                key = (partid, mc_id)
                result.update(
                    {
                        "core_partid_mc_ostd": (
                            self.outstanding_by_partid_mc.get(key, 0)
                        ),
                        "core_partid_mc_ostd_peak": (
                            self.peak_outstanding_by_partid_mc.get(
                                key,
                                0,
                            )
                        ),
                    }
                )
        return result

    def reset_interval_peak(self) -> None:
        self.peak_outstanding = self.outstanding
        self.peak_outstanding_by_partid = dict(
            self.outstanding_by_partid
        )
        self.peak_outstanding_by_partid_mc = dict(
            self.outstanding_by_partid_mc
        )


@dataclass
class RequesterRuntime:
    config: RequesterConfig
    core_pool: CoreOstdPool
    configured_partids: Tuple[int, ...] = ()
    destination_mc_ids: Tuple[str, ...] = ()
    cbusy_response_enable: bool = True
    outstanding: int = 0
    issued: int = 0
    completed: int = 0
    generated: int = 0
    pending: int = 0
    backpressure_ns: float = 0.0
    generated_by_partid: Dict[int, int] = field(default_factory=dict)
    pending_by_partid: Dict[int, int] = field(default_factory=dict)
    outstanding_by_partid: Dict[int, int] = field(default_factory=dict)
    peak_outstanding_by_partid: Dict[int, int] = field(default_factory=dict)
    issued_by_partid: Dict[int, int] = field(default_factory=dict)
    completed_by_partid: Dict[int, int] = field(default_factory=dict)
    backpressure_by_partid: Dict[int, float] = field(default_factory=dict)
    cbusy_stall_by_partid: Dict[int, float] = field(default_factory=dict)
    stall_by_reason_partid: Dict[Tuple[int, str], float] = field(
        default_factory=dict
    )
    cbusy_feedback_by_partid: Dict[int, Dict[str, Tuple[int, int]]] = field(
        default_factory=dict
    )
    cbusy_transitions_by_partid: Dict[int, int] = field(default_factory=dict)
    outstanding_by_partid_mc: Dict[Tuple[int, str], int] = field(
        default_factory=dict
    )
    peak_outstanding_by_partid_mc: Dict[Tuple[int, str], int] = field(
        default_factory=dict
    )
    issued_by_partid_mc: Dict[Tuple[int, str], int] = field(
        default_factory=dict
    )
    completed_by_partid_mc: Dict[Tuple[int, str], int] = field(
        default_factory=dict
    )
    stall_by_partid_mc: Dict[Tuple[int, str], float] = field(
        default_factory=dict
    )
    _last_block_reason: Dict[Tuple[int, str], str] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        for partid in self.configured_partids:
            self._ensure_partid(partid)
            for mc_id in self.destination_mc_ids:
                self._ensure_partid_mc(partid, mc_id)

    def _ensure_partid(self, partid: int) -> None:
        self.outstanding_by_partid.setdefault(partid, 0)
        self.peak_outstanding_by_partid.setdefault(partid, 0)
        self.issued_by_partid.setdefault(partid, 0)
        self.completed_by_partid.setdefault(partid, 0)
        self.generated_by_partid.setdefault(partid, 0)
        self.pending_by_partid.setdefault(partid, 0)
        self.backpressure_by_partid.setdefault(partid, 0.0)
        self.cbusy_stall_by_partid.setdefault(partid, 0.0)
        self.cbusy_feedback_by_partid.setdefault(partid, {})
        self.cbusy_transitions_by_partid.setdefault(partid, 0)

    def _ensure_partid_mc(self, partid: int, mc_id: str) -> None:
        key = (partid, mc_id)
        self.outstanding_by_partid_mc.setdefault(key, 0)
        self.peak_outstanding_by_partid_mc.setdefault(key, 0)
        self.issued_by_partid_mc.setdefault(key, 0)
        self.completed_by_partid_mc.setdefault(key, 0)
        self.stall_by_partid_mc.setdefault(key, 0.0)

    def mark_pending(self, pending: bool) -> None:
        self.core_pool.mark_pending(self.config.id, pending)

    def on_generated(self, partid: int) -> None:
        self._ensure_partid(partid)
        self.generated += 1
        self.pending += 1
        self.generated_by_partid[partid] += 1
        self.pending_by_partid[partid] += 1
        self.mark_pending(True)

    def on_pending_cancelled(self, partid: int) -> None:
        self._ensure_partid(partid)
        self.pending = max(0, self.pending - 1)
        self.pending_by_partid[partid] = max(
            0,
            self.pending_by_partid[partid] - 1,
        )
        self.mark_pending(self.pending > 0)

    def cbusy_level(self, partid: int, mc_id: str = "") -> int:
        self._ensure_partid(partid)
        feedback = self.cbusy_feedback_by_partid[partid]
        return max((level for level, _ in feedback.values()), default=0)

    def effective_max_outstanding(
        self,
        partid: int,
        mc_id: str = "",
    ) -> int:
        self._ensure_partid(partid)
        if not self.cbusy_response_enable:
            return self.config.max_outstanding
        feedback = self.cbusy_feedback_by_partid[partid]
        level = self.cbusy_level(partid)
        caps = [
            cap
            for source_level, cap in feedback.values()
            if source_level == level and level > 0
        ]
        return max(
            1,
            min(
                self.config.max_outstanding,
                min(caps) if caps else self.config.max_outstanding,
            ),
        )

    def admission_block_reason(
        self,
        partid: int,
        mc_id: str,
    ) -> Optional[str]:
        self._ensure_partid(partid)
        self._ensure_partid_mc(partid, mc_id)
        if self.outstanding >= self.config.max_outstanding:
            return "thread_ostd"
        level = self.cbusy_level(partid)
        effective = self.effective_max_outstanding(partid)
        if (
            self.cbusy_response_enable
            and level > 0
            and self.core_pool.outstanding_by_partid.get(partid, 0)
            >= effective
        ):
            return "cbusy"
        return self.core_pool.block_reason(self.config.id)

    def can_issue(self, partid: int, mc_id: str) -> bool:
        reason = self.admission_block_reason(partid, mc_id)
        key = (partid, mc_id)
        if reason is None:
            self._last_block_reason.pop(key, None)
            return True
        self._last_block_reason[key] = reason
        return False

    def last_block_reason(self, partid: int, mc_id: str) -> str:
        return self._last_block_reason.get(
            (partid, mc_id),
            "thread_ostd",
        )

    def blocked_by_cbusy(self, partid: int, mc_id: str) -> bool:
        return self.last_block_reason(partid, mc_id) == "cbusy"

    def set_cbusy(
        self,
        msc_id: str,
        partid: int,
        level: int,
        cap: int,
    ) -> None:
        self._ensure_partid(partid)
        before = self.cbusy_level(partid)
        self.cbusy_feedback_by_partid[partid][msc_id] = (
            max(0, min(3, level)),
            max(1, cap),
        )
        if self.cbusy_level(partid) != before:
            self.cbusy_transitions_by_partid[partid] += 1

    def on_issue(self, partid: int, mc_id: str) -> None:
        self._ensure_partid(partid)
        self._ensure_partid_mc(partid, mc_id)
        self.core_pool.allocate(
            self.config.id,
            partid=partid,
            mc_id=mc_id,
            remains_pending=self.pending > 1,
        )
        self.pending = max(0, self.pending - 1)
        self.pending_by_partid[partid] = max(
            0,
            self.pending_by_partid[partid] - 1,
        )
        self.outstanding += 1
        self.issued += 1
        self.outstanding_by_partid[partid] += 1
        self.issued_by_partid[partid] += 1
        key = (partid, mc_id)
        self.outstanding_by_partid_mc[key] += 1
        self.issued_by_partid_mc[key] += 1
        self.peak_outstanding_by_partid[partid] = max(
            self.peak_outstanding_by_partid[partid],
            self.outstanding_by_partid[partid],
        )
        self.peak_outstanding_by_partid_mc[key] = max(
            self.peak_outstanding_by_partid_mc[key],
            self.outstanding_by_partid_mc[key],
        )

    def on_completion(self, partid: int, mc_id: str) -> None:
        self._ensure_partid(partid)
        self._ensure_partid_mc(partid, mc_id)
        self.core_pool.release(
            self.config.id,
            partid=partid,
            mc_id=mc_id,
        )
        self.outstanding = max(0, self.outstanding - 1)
        self.completed += 1
        self.outstanding_by_partid[partid] = max(
            0,
            self.outstanding_by_partid[partid] - 1,
        )
        self.completed_by_partid[partid] += 1
        key = (partid, mc_id)
        self.outstanding_by_partid_mc[key] = max(
            0,
            self.outstanding_by_partid_mc[key] - 1,
        )
        self.completed_by_partid_mc[key] += 1

    def on_backpressure(
        self,
        partid: int,
        mc_id: str,
        delay_ns: float,
        reason: str,
    ) -> None:
        self._ensure_partid(partid)
        self._ensure_partid_mc(partid, mc_id)
        self.backpressure_ns += delay_ns
        self.backpressure_by_partid[partid] += delay_ns
        self.stall_by_reason_partid[(partid, reason)] = (
            self.stall_by_reason_partid.get((partid, reason), 0.0)
            + delay_ns
        )
        self.stall_by_partid_mc[(partid, mc_id)] += delay_ns
        if reason == "cbusy":
            self.cbusy_stall_by_partid[partid] += delay_ns

    def capture_partid_rows(self) -> List[Dict[str, object]]:
        partids = sorted(
            set(self.configured_partids)
            | set(self.outstanding_by_partid)
            | set(self.issued_by_partid)
        )
        rows = []
        for partid in partids:
            self._ensure_partid(partid)
            per_destination = {
                mc_id: {
                    "outstanding": self.outstanding_by_partid_mc[
                        (partid, mc_id)
                    ],
                    "effective_limit": self.effective_max_outstanding(
                        partid,
                        mc_id,
                    ),
                    "cbusy_level": self.cbusy_level(partid, mc_id),
                    "core_outstanding": (
                        self.core_pool.partid_mc_outstanding(
                            partid,
                            mc_id,
                        )
                    ),
                }
                for mc_id in self.destination_mc_ids
            }
            rows.append(
                {
                    "requester_id": self.config.id,
                    "core_id": self.core_pool.core_id,
                    "partid": partid,
                    "generated": self.generated_by_partid[partid],
                    "source_pending": self.pending_by_partid[partid],
                    "outstanding": self.outstanding_by_partid[partid],
                    "peak_outstanding": self.peak_outstanding_by_partid[partid],
                    "max_outstanding": self.config.max_outstanding,
                    "effective_max_outstanding": (
                        self.effective_max_outstanding(partid)
                    ),
                    "cbusy_level": self.cbusy_level(partid),
                    "cbusy_stall_ns": self.cbusy_stall_by_partid[partid],
                    "thread_ostd_stall_ns": self.stall_by_reason_partid.get(
                        (partid, "thread_ostd"),
                        0.0,
                    ),
                    "core_ostd_stall_ns": sum(
                        self.stall_by_reason_partid.get(
                            (partid, reason),
                            0.0,
                        )
                        for reason in (
                            "core_ostd",
                            "core_round_robin",
                        )
                    ),
                    "req_ring_stall_ns": (
                        self.stall_by_reason_partid.get(
                            (partid, "req_ring"),
                            0.0,
                        )
                    ),
                    "configured_ostd_stall_ns": max(
                        0.0,
                        self.backpressure_by_partid[partid]
                        - self.cbusy_stall_by_partid[partid],
                    ),
                    "cbusy_transitions": self.cbusy_transitions_by_partid[
                        partid
                    ],
                    "issued": self.issued_by_partid[partid],
                    "completed": self.completed_by_partid[partid],
                    "backpressure_ns": self.backpressure_by_partid[partid],
                    "per_destination": per_destination,
                    **self.core_pool.status(partid),
                }
            )
            self.peak_outstanding_by_partid[partid] = (
                self.outstanding_by_partid[partid]
            )
        return rows

    def capture_partid_mc_rows(self) -> List[Dict[str, object]]:
        rows = []
        for partid in sorted(self.configured_partids):
            for mc_id in self.destination_mc_ids:
                self._ensure_partid_mc(partid, mc_id)
                key = (partid, mc_id)
                rows.append(
                    {
                        "requester_id": self.config.id,
                        "core_id": self.core_pool.core_id,
                        "partid": partid,
                        "destination_mc": mc_id,
                        "outstanding": self.outstanding_by_partid_mc[key],
                        "peak_outstanding": (
                            self.peak_outstanding_by_partid_mc[key]
                        ),
                        "effective_max_outstanding": (
                            self.effective_max_outstanding(partid, mc_id)
                        ),
                        "cbusy_level": self.cbusy_level(partid, mc_id),
                        "issued": self.issued_by_partid_mc[key],
                        "completed": self.completed_by_partid_mc[key],
                        "stall_ns": self.stall_by_partid_mc[key],
                        **self.core_pool.status(partid, mc_id),
                    }
                )
                self.peak_outstanding_by_partid_mc[key] = (
                    self.outstanding_by_partid_mc[key]
                )
        return rows
