from __future__ import annotations

from typing import Callable, Dict, List, Optional, Protocol, Sequence

from .telemetry import ControlDecision, MonitorSnapshot
from .transaction import Transaction


class EndpointPort(Protocol):
    def can_accept(self, transaction: Transaction) -> bool:
        ...

    def accept(self, transaction: Transaction) -> None:
        ...


class RingTransport(Protocol):
    def can_inject(
        self,
        source_node: str,
        destination_node: str,
        channel: str,
    ) -> bool:
        ...

    def transmit(
        self,
        transaction: Transaction,
        channel: str,
        downstream: EndpointPort,
        *,
        source_node: str,
        destination_node: str,
    ) -> bool:
        ...


class CacheLookupPipeline(EndpointPort, Protocol):
    def lookup(self, transaction: Transaction) -> None:
        ...


class ReplacementPolicy(Protocol):
    def ordered_victims(
        self,
        set_index: int,
        transaction: Transaction,
        eligible_ways: Sequence[int],
    ) -> Sequence[int]:
        ...


class MshrTable(Protocol):
    def merge_or_allocate(
        self,
        transaction: Transaction,
    ) -> bool:
        ...

    def release(self, line_address: int) -> Sequence[Transaction]:
        ...


class McReadinessPolicy(Protocol):
    def eligible(
        self,
        transactions: Sequence[Transaction],
    ) -> Sequence[bool]:
        ...


class McScheduler(Protocol):
    def select(
        self,
        transactions: Sequence[Transaction],
        eligible: Sequence[bool],
    ) -> Optional[int]:
        ...


class MonitorSource(Protocol):
    def monitor_snapshot(self, interval_ns: float) -> MonitorSnapshot:
        ...


class ControlPolicy(Protocol):
    name: str

    def on_interval(
        self,
        interval_index: int,
        time_ns: float,
        metrics_by_partid: Dict[int, Dict[str, float]],
    ) -> List[ControlDecision]:
        ...


class ValidationHook(Protocol):
    name: str

    def validate(
        self,
        transaction: Transaction,
        emit: Callable[[str, Dict[str, object]], None],
    ) -> None:
        ...
