from __future__ import annotations

from dataclasses import dataclass

from src.config.schema import RequesterConfig


@dataclass
class RequesterRuntime:
    config: RequesterConfig
    outstanding: int = 0
    issued: int = 0
    completed: int = 0
    backpressure_ns: float = 0.0

    def can_issue(self) -> bool:
        return self.outstanding < self.config.max_outstanding

    def on_issue(self) -> None:
        self.outstanding += 1
        self.issued += 1

    def on_completion(self) -> None:
        self.outstanding = max(0, self.outstanding - 1)
        self.completed += 1
