from __future__ import annotations

import heapq
from typing import Callable, List

from .event import Event


class SimulationKernel:
    def __init__(self) -> None:
        self.now_ns = 0.0
        self._sequence = 0
        self._events: List[Event] = []
        self.events_executed = 0

    def schedule_at(self, time_ns: float, callback: Callable[[], None], name: str = "") -> None:
        if time_ns < self.now_ns:
            raise ValueError(f"Cannot schedule event in the past: {time_ns} < {self.now_ns}")
        self._sequence += 1
        heapq.heappush(self._events, Event(float(time_ns), self._sequence, callback, name))

    def schedule(self, delay_ns: float, callback: Callable[[], None], name: str = "") -> None:
        self.schedule_at(self.now_ns + max(0.0, float(delay_ns)), callback, name)

    def run(self, until_ns: float) -> None:
        until_ns = float(until_ns)
        while self._events and self._events[0].time_ns <= until_ns:
            event = heapq.heappop(self._events)
            self.now_ns = event.time_ns
            event.callback()
            self.events_executed += 1
        self.now_ns = until_ns

    @property
    def pending_events(self) -> int:
        return len(self._events)
