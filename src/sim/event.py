from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(order=True)
class Event:
    time_ns: float
    sequence: int
    callback: Callable[[], None] = field(compare=False)
    name: str = field(default="", compare=False)
