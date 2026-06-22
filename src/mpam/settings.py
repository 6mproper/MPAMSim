from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Iterable, Optional

from src.config.schema import MPAMSettingConfig


@dataclass
class MPAMSetting:
    partid: int
    cache_portion_bitmap: Optional[str] = None
    cache_min_percent: float = 0.0
    cache_max_percent: Optional[float] = None
    bw_max_gbps: Optional[float] = None
    bw_min_gbps: Optional[float] = None
    bw_limit_mode: str = "hardlimit"
    mc_qos: int = 0
    monitor_enable: bool = True
    cpbm_enable: bool = True
    cmin_enable: bool = True
    cmax_enable: bool = True
    bmin_enable: bool = True
    bmax_enable: bool = True
    mc_qos_enable: bool = True
    cbusy_enable: bool = False
    cbusy_l1_ostd: int = 24
    cbusy_l2_ostd: int = 12
    cbusy_l3_ostd: int = 4

    @property
    def cpbm(self) -> Optional[str]:
        return self.cache_portion_bitmap

    @property
    def cmin(self) -> float:
        return self.cache_min_percent

    @property
    def cmax(self) -> Optional[float]:
        return self.cache_max_percent

    @property
    def bmin(self) -> Optional[float]:
        return self.bw_min_gbps

    @property
    def bmax(self) -> Optional[float]:
        return self.bw_max_gbps


class SettingsTable:
    def __init__(self, controls: Iterable[MPAMSettingConfig] = ()) -> None:
        self._settings: Dict[int, MPAMSetting] = {}
        for control in controls:
            self._settings[control.partid] = MPAMSetting(
                partid=control.partid,
                cache_portion_bitmap=control.cache_portion_bitmap,
                cache_min_percent=control.cache_min_percent,
                cache_max_percent=control.cache_max_percent,
                bw_max_gbps=control.bw_max_gbps,
                bw_min_gbps=control.bw_min_gbps,
                bw_limit_mode=control.bw_limit_mode,
                mc_qos=control.mc_qos,
                monitor_enable=control.monitor_enable,
                cpbm_enable=control.cpbm_enable,
                cmin_enable=control.cmin_enable,
                cmax_enable=control.cmax_enable,
                bmin_enable=control.bmin_enable,
                bmax_enable=control.bmax_enable,
                mc_qos_enable=control.mc_qos_enable,
                cbusy_enable=control.cbusy_enable,
                cbusy_l1_ostd=control.cbusy_l1_ostd,
                cbusy_l2_ostd=control.cbusy_l2_ostd,
                cbusy_l3_ostd=control.cbusy_l3_ostd,
            )

    def lookup(self, partid: int) -> MPAMSetting:
        return self._settings.get(partid, MPAMSetting(partid=partid))

    def update(self, partid: int, field: str, value: object) -> object:
        current = self.lookup(partid)
        if not hasattr(current, field):
            raise ValueError(f"Unsupported MPAM setting field: {field}")
        old_value = getattr(current, field)
        self._settings[partid] = replace(current, **{field: value})
        return old_value

    def items(self):
        return self._settings.items()

# Resctrl-style software group support (step 7)
# CTRL_MON group: maps task/CPU to PARTID for both control and monitoring
# MON group: maps task/CPU to PMG for monitoring only
# Task group assignment takes priority over CPU default assignment
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SoftwareGroup:
    name: str
    group_type: str  # "ctrl_mon" or "mon"
    partid: int
    pmg: int = 0
    cpus: List[int] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)

    def applies_to_cpu(self, cpu_id: int) -> bool:
        return not self.cpus or cpu_id in self.cpus


@dataclass
class SoftwareGroupConfig:
    groups: List[SoftwareGroup] = field(default_factory=list)

    def resolve_partid(self, cpu_id: int, task_name: str = "", default_partid: int = 0) -> int:
        for group in self.groups:
            if group.group_type != "ctrl_mon":
                continue
            if task_name and task_name in group.tasks:
                return group.partid
        for group in self.groups:
            if group.group_type != "ctrl_mon":
                continue
            if group.applies_to_cpu(cpu_id):
                return group.partid
        return default_partid

    def resolve_pmg(self, cpu_id: int, task_name: str = "", default_pmg: int = 0) -> int:
        for group in self.groups:
            if group.group_type not in ("ctrl_mon", "mon"):
                continue
            if task_name and task_name in group.tasks:
                return group.pmg
        for group in self.groups:
            if group.group_type not in ("ctrl_mon", "mon"):
                continue
            if group.applies_to_cpu(cpu_id):
                return group.pmg
        return default_pmg
