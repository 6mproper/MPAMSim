from __future__ import annotations

from typing import Dict, Iterable, List

from src.mpam.control import ControlUpdate
from src.mpam.settings import SettingsTable

from .policy_base import PolicyBase


class ClosedLoopQoSPolicy(PolicyBase):
    name = "closed_loop_qos"

    def __init__(
        self,
        params: Dict[str, object],
        target_p99_by_partid: Dict[int, float],
        mc_tables: Dict[str, SettingsTable],
    ) -> None:
        self.params = params
        self.targets = target_p99_by_partid
        self.mc_tables = mc_tables
        self.protected = [int(value) for value in params.get("protected_partids", list(self.targets))]
        self.background = [int(value) for value in params.get("background_partids", [])]
        self.max_step_percent = float(params.get("max_bw_step_percent", 10.0))
        self.priority_min = int(params.get("priority_min", 0))
        self.priority_max = int(params.get("priority_max", 15))
        self.hysteresis = float(params.get("p99_hysteresis", 0.10))
        self.min_hold_intervals = int(params.get("min_hold_intervals", 3))
        self._last_update_interval = -self.min_hold_intervals
        self._initial_caps = {
            (msc_id, partid): table.lookup(partid).bw_max_gbps
            for msc_id, table in mc_tables.items()
            for partid in self.background
        }

    def on_interval(
        self,
        interval_index: int,
        time_ns: float,
        metrics_by_partid: Dict[int, Dict[str, float]],
    ) -> List[ControlUpdate]:
        if interval_index - self._last_update_interval < self.min_hold_intervals:
            return []

        violations = []
        for partid in self.protected:
            metrics = metrics_by_partid.get(partid)
            target = self.targets.get(partid)
            if not metrics or target is None or metrics.get("requests", 0) == 0:
                continue
            if metrics.get("p99_latency_ns", 0.0) > target * (1.0 + self.hysteresis):
                violations.append((partid, metrics["p99_latency_ns"], target))

        if violations:
            self._last_update_interval = interval_index
            reason = ", ".join(
                "PARTID {} p99 {:.1f}ns > {:.1f}ns".format(partid, actual, target)
                for partid, actual, target in violations
            )
            return self._protect_updates(reason)

        comfortably_below = all(
            metrics_by_partid.get(partid, {}).get("p99_latency_ns", float("inf"))
            < self.targets.get(partid, 0.0) * (1.0 - self.hysteresis)
            for partid in self.protected
            if partid in self.targets
        )
        if comfortably_below and self.protected:
            updates = self._relax_updates("protected latency below hysteresis band")
            if updates:
                self._last_update_interval = interval_index
            return updates
        return []

    def _protect_updates(self, reason: str) -> List[ControlUpdate]:
        updates: List[ControlUpdate] = []
        for msc_id, table in self.mc_tables.items():
            for partid in self.protected:
                current = table.lookup(partid).priority
                new_priority = min(self.priority_max, current + 1)
                if new_priority != current:
                    updates.append(
                        ControlUpdate(msc_id, partid, "priority", new_priority, reason, self.name)
                    )
            for partid in self.background:
                cap = table.lookup(partid).bw_max_gbps
                if cap is None:
                    continue
                new_cap = max(0.001, cap * (1.0 - self.max_step_percent / 100.0))
                if abs(new_cap - cap) > 1e-9:
                    updates.append(
                        ControlUpdate(msc_id, partid, "bw_max_gbps", new_cap, reason, self.name)
                    )
        return updates

    def _relax_updates(self, reason: str) -> List[ControlUpdate]:
        updates: List[ControlUpdate] = []
        for msc_id, table in self.mc_tables.items():
            for partid in self.background:
                initial_cap = self._initial_caps.get((msc_id, partid))
                current = table.lookup(partid).bw_max_gbps
                if initial_cap is None or current is None or current >= initial_cap:
                    continue
                new_cap = min(initial_cap, current * (1.0 + self.max_step_percent / 100.0))
                updates.append(
                    ControlUpdate(msc_id, partid, "bw_max_gbps", new_cap, reason, self.name)
                )
        return updates
