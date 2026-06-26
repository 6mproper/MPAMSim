from __future__ import annotations

from typing import Dict, List

from src.config.schema import PolicyConfig
from src.mpam.settings import SettingsTable

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
        if config.name == "no_control":
            policies.append(NoControlPolicy())
        else:
            policies.append(StaticMPAMPolicy())
    return policies
