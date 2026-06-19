from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.config.schema import RequesterConfig


@dataclass
class RequesterRuntime:
    config: RequesterConfig
    configured_partids: Tuple[int, ...] = ()
    outstanding: int = 0
    issued: int = 0
    completed: int = 0
    backpressure_ns: float = 0.0
    outstanding_by_partid: Dict[int, int] = field(default_factory=dict)
    peak_outstanding_by_partid: Dict[int, int] = field(default_factory=dict)
    issued_by_partid: Dict[int, int] = field(default_factory=dict)
    completed_by_partid: Dict[int, int] = field(default_factory=dict)
    backpressure_by_partid: Dict[int, float] = field(default_factory=dict)
    cbusy_stall_by_partid: Dict[int, float] = field(default_factory=dict)
    cbusy_feedback_by_partid: Dict[int, Dict[str, Tuple[int, int]]] = field(
        default_factory=dict
    )
    cbusy_transitions_by_partid: Dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for partid in self.configured_partids:
            self._ensure_partid(partid)

    def _ensure_partid(self, partid: int) -> None:
        self.outstanding_by_partid.setdefault(partid, 0)
        self.peak_outstanding_by_partid.setdefault(partid, 0)
        self.issued_by_partid.setdefault(partid, 0)
        self.completed_by_partid.setdefault(partid, 0)
        self.backpressure_by_partid.setdefault(partid, 0.0)
        self.cbusy_stall_by_partid.setdefault(partid, 0.0)
        self.cbusy_feedback_by_partid.setdefault(partid, {})
        self.cbusy_transitions_by_partid.setdefault(partid, 0)

    def cbusy_level(self, partid: int) -> int:
        self._ensure_partid(partid)
        return max(
            (
                level
                for level, _ in self.cbusy_feedback_by_partid[
                    partid
                ].values()
            ),
            default=0,
        )

    def effective_max_outstanding(self, partid: int) -> int:
        self._ensure_partid(partid)
        level = self.cbusy_level(partid)
        caps = [
            cap
            for source_level, cap in self.cbusy_feedback_by_partid[
                partid
            ].values()
            if source_level == level and level > 0
        ]
        return max(
            1,
            min(
                self.config.max_outstanding,
                min(caps) if caps else self.config.max_outstanding,
            ),
        )

    def can_issue(self, partid: int) -> bool:
        self._ensure_partid(partid)
        return (
            self.outstanding < self.config.max_outstanding
            and self.outstanding_by_partid[partid]
            < self.effective_max_outstanding(partid)
        )

    def blocked_by_cbusy(self, partid: int) -> bool:
        self._ensure_partid(partid)
        return (
            self.outstanding < self.config.max_outstanding
            and self.outstanding_by_partid[partid]
            >= self.effective_max_outstanding(partid)
            and self.cbusy_level(partid) > 0
        )

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

    def on_issue(self, partid: int) -> None:
        self._ensure_partid(partid)
        self.outstanding += 1
        self.issued += 1
        self.outstanding_by_partid[partid] += 1
        self.issued_by_partid[partid] += 1
        self.peak_outstanding_by_partid[partid] = max(
            self.peak_outstanding_by_partid[partid],
            self.outstanding_by_partid[partid],
        )

    def on_completion(self, partid: int) -> None:
        self._ensure_partid(partid)
        self.outstanding = max(0, self.outstanding - 1)
        self.completed += 1
        self.outstanding_by_partid[partid] = max(
            0,
            self.outstanding_by_partid[partid] - 1,
        )
        self.completed_by_partid[partid] += 1

    def on_backpressure(
        self,
        partid: int,
        delay_ns: float,
        cbusy: bool = False,
    ) -> None:
        self._ensure_partid(partid)
        self.backpressure_ns += delay_ns
        self.backpressure_by_partid[partid] += delay_ns
        if cbusy:
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
            rows.append(
                {
                    "requester_id": self.config.id,
                    "partid": partid,
                    "outstanding": self.outstanding_by_partid[partid],
                    "peak_outstanding": self.peak_outstanding_by_partid[partid],
                    "max_outstanding": self.config.max_outstanding,
                    "effective_max_outstanding": (
                        self.effective_max_outstanding(partid)
                    ),
                    "cbusy_level": self.cbusy_level(partid),
                    "cbusy_stall_ns": self.cbusy_stall_by_partid[partid],
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
                }
            )
            self.peak_outstanding_by_partid[partid] = (
                self.outstanding_by_partid[partid]
            )
        return rows
