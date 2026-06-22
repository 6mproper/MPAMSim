from __future__ import annotations

from typing import Dict, List

from src.config.schema import PolicyConfig
from src.mpam.settings import SettingsTable

from .closed_loop import ClosedLoopQoSPolicy
from .policy_base import PolicyBase


class NoControlPolicy(PolicyBase):
    name = "no_control"


class StaticMPAMPolicy(PolicyBase):
    name = "static_mpam"


def build_policies(
    configs: List[PolicyConfig],
    targets: Dict[int, float],
    mc_tables: Dict[str, SettingsTable],
) -> List[PolicyBase]:
    policies: List[PolicyBase] = []
    for config in configs:
        if config.name == "closed_loop_qos":
            policies.append(ClosedLoopQoSPolicy(config.params, targets, mc_tables))
        elif config.name in ("closed_loop_comprehensive", "combined"):
            policies.append(ClosedLoopQoSPolicy(config.params, targets, mc_tables))
        elif config.name == "no_control":
            policies.append(NoControlPolicy())
        elif config.name == "static_mpam":
            policies.append(StaticMPAMPolicy())
        else:
            raise ValueError(
                f"Unknown policy: {config.name}. "
                f"Supported: no_control, static_mpam, closed_loop_qos, closed_loop_comprehensive"
            )
    return policies
