from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ControlUpdate:
    target_msc: str
    partid: int
    field: str
    value: Any
    reason: str
    policy: str = ""
