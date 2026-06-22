from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .transaction import Transaction


RingChannel = Literal["req", "rsp", "dat"]
RingDirection = Literal["cw", "ccw"]


@dataclass
class RingFlit:
    transfer_id: int
    transaction: Transaction
    channel: RingChannel
    direction: RingDirection
    source_node: str
    destination_node: str
    flit_index: int
    flit_count: int
    injected_time_ns: float
    hops: int = 0
    failed_ejections: int = 0
    full_laps: int = 0
