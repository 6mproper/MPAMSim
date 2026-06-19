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

    def __post_init__(self) -> None:
        for partid in self.configured_partids:
            self._ensure_partid(partid)

    def _ensure_partid(self, partid: int) -> None:
        self.outstanding_by_partid.setdefault(partid, 0)
        self.peak_outstanding_by_partid.setdefault(partid, 0)
        self.issued_by_partid.setdefault(partid, 0)
        self.completed_by_partid.setdefault(partid, 0)
        self.backpressure_by_partid.setdefault(partid, 0.0)

    def can_issue(self) -> bool:
        return self.outstanding < self.config.max_outstanding

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

    def on_backpressure(self, partid: int, delay_ns: float) -> None:
        self._ensure_partid(partid)
        self.backpressure_ns += delay_ns
        self.backpressure_by_partid[partid] += delay_ns

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
                    "issued": self.issued_by_partid[partid],
                    "completed": self.completed_by_partid[partid],
                    "backpressure_ns": self.backpressure_by_partid[partid],
                }
            )
            self.peak_outstanding_by_partid[partid] = (
                self.outstanding_by_partid[partid]
            )
        return rows
