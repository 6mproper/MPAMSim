from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Component(ABC):
    def __init__(self, component_id: str) -> None:
        self.component_id = component_id

    @abstractmethod
    def monitor_snapshot(self, interval_ns: float) -> Dict[str, Any]:
        raise NotImplementedError
