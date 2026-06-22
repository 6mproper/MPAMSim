from __future__ import annotations

from typing import Dict, List

from src.contracts.telemetry import ControlDecision


class PolicyBase:
    name = "policy_base"

    def on_interval(
        self,
        interval_index: int,
        time_ns: float,
        metrics_by_partid: Dict[int, Dict[str, float]],
    ) -> List[ControlDecision]:
        return []
