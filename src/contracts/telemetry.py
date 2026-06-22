from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple


class MetricSemantic(str, Enum):
    ACTUAL = "actual"
    RAW_MONITOR = "raw_monitor"
    FILTERED_MONITOR = "filtered_monitor"
    CONFIGURED_TARGET = "configured_target"
    EFFECTIVE_TARGET = "effective_target"
    CONTROL_STATE = "control_state"


MetricValue = Any


def _metric_semantic(metric: str) -> MetricSemantic:
    if metric.startswith("configured_"):
        return MetricSemantic.CONFIGURED_TARGET
    if metric.startswith("effective_") or metric in {
        "cmin",
        "cmax",
        "bmin_gbps",
        "bmax_gbps",
        "base_qos",
    }:
        return MetricSemantic.EFFECTIVE_TARGET
    if metric.startswith("raw_"):
        return MetricSemantic.RAW_MONITOR
    if metric.startswith("filtered_"):
        return MetricSemantic.FILTERED_MONITOR
    if metric.endswith("_enable") or metric in {
        "cbusy_level",
        "limit_mode",
        "enforcement_enabled",
    }:
        return MetricSemantic.CONTROL_STATE
    return MetricSemantic.ACTUAL


def _metric_unit(metric: str) -> str:
    if metric.endswith("_ns"):
        return "ns"
    if metric.endswith("_gbps"):
        return "Gbps"
    if metric.endswith("_bytes") or metric == "bytes":
        return "byte"
    if metric.endswith("_percent"):
        return "%"
    if (
        metric.endswith("_ratio")
        or metric.endswith("_utilization")
        or metric.endswith("_duty")
        or metric == "utilization"
    ):
        return "ratio"
    if "qos" in metric or metric.endswith("_level"):
        return "level"
    if metric.endswith("_count") or metric.endswith("_events"):
        return "count"
    return "value"


def _is_scalar(value: object) -> bool:
    return value is None or isinstance(
        value,
        (bool, int, float, str),
    )


@dataclass(frozen=True)
class MonitorSample:
    time_ns: float
    resource_type: str
    resource_id: str
    local_cycle: Optional[int]
    partid: Optional[int]
    pmg: Optional[int]
    metric: str
    value: MetricValue
    unit: str
    semantic: MetricSemantic
    sample_id: str
    observation_id: str = ""
    cause_id: Optional[str] = None

    def to_row(self) -> Dict[str, object]:
        return {
            "time_ns": self.time_ns,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "local_cycle": self.local_cycle,
            "partid": self.partid,
            "pmg": self.pmg,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "semantic": self.semantic.value,
            "sample_id": self.sample_id,
            "observation_id": self.observation_id,
            "cause_id": self.cause_id,
        }


@dataclass(frozen=True)
class MonitorSnapshot:
    time_ns: float
    resource_type: str
    resource_id: str
    interval_ns: float
    sample_id: str
    payload: Mapping[str, object]
    local_cycle: Optional[int] = None
    samples: Tuple[MonitorSample, ...] = ()

    @classmethod
    def from_payload(
        cls,
        time_ns: float,
        resource_type: str,
        resource_id: str,
        interval_ns: float,
        sample_id: str,
        payload: Mapping[str, object],
        local_cycle: Optional[int] = None,
    ) -> "MonitorSnapshot":
        samples: List[MonitorSample] = [
            MonitorSample(
                time_ns=time_ns,
                resource_type=resource_type,
                resource_id=resource_id,
                local_cycle=local_cycle,
                partid=None,
                pmg=None,
                metric="snapshot",
                value=1,
                unit="event",
                semantic=MetricSemantic.RAW_MONITOR,
                sample_id=sample_id,
            )
        ]

        def add_sample(
            metric: str,
            value: object,
            partid: Optional[int] = None,
            pmg: Optional[int] = None,
        ) -> None:
            samples.append(
                MonitorSample(
                    time_ns=time_ns,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    local_cycle=local_cycle,
                    partid=partid,
                    pmg=pmg,
                    metric=metric,
                    value=value,
                    unit=_metric_unit(metric),
                    semantic=_metric_semantic(metric),
                    sample_id=f"{sample_id}:{len(samples)}",
                )
            )

        for metric, value in payload.items():
            if metric in {
                "msc_id",
                "msc_type",
                "per_partid",
                "monitor_groups",
                "requesters",
            }:
                continue
            if _is_scalar(value):
                add_sample(metric, value)

        per_partid = payload.get("per_partid", {})
        if isinstance(per_partid, Mapping):
            for partid_text, values in per_partid.items():
                if not isinstance(values, Mapping):
                    continue
                partid = int(partid_text)
                for metric, value in values.items():
                    if _is_scalar(value):
                        add_sample(metric, value, partid=partid)

        monitor_groups = payload.get("monitor_groups", {})
        if isinstance(monitor_groups, Mapping):
            for values in monitor_groups.values():
                if not isinstance(values, Mapping):
                    continue
                partid = int(values.get("partid", 0))
                pmg = int(values.get("pmg", 0))
                for metric, value in values.items():
                    if metric in {"partid", "pmg"}:
                        continue
                    if _is_scalar(value):
                        add_sample(
                            metric,
                            value,
                            partid=partid,
                            pmg=pmg,
                        )

        return cls(
            time_ns=time_ns,
            resource_type=resource_type,
            resource_id=resource_id,
            interval_ns=interval_ns,
            sample_id=sample_id,
            payload=dict(payload),
            local_cycle=local_cycle,
            samples=tuple(samples),
        )

    def to_row(self) -> Dict[str, object]:
        return {
            "msc_id": self.resource_id,
            "msc_type": self.resource_type,
            **dict(self.payload),
        }


@dataclass(frozen=True)
class ControlDecision:
    target_resource_id: str
    partid: int
    field: str
    value: object
    reason: str
    policy: str = ""
    pmg: Optional[int] = None
    decision_id: str = ""
    monitor_sample_id: str = ""
    observation_id: str = ""
    action_effective_time_ns: Optional[float] = None

    @property
    def target_msc(self) -> str:
        return self.target_resource_id

    def with_context(
        self,
        decision_id: str,
        monitor_sample_id: str,
        action_effective_time_ns: float,
        observation_id: str = "",
    ) -> "ControlDecision":
        return replace(
            self,
            decision_id=decision_id,
            monitor_sample_id=monitor_sample_id,
            action_effective_time_ns=action_effective_time_ns,
            observation_id=observation_id,
        )


@dataclass(frozen=True)
class ControlEvent:
    event_id: str
    event_time_ns: float
    resource_type: str
    resource_id: str
    partid: int
    event_type: str
    old_state: object
    new_state: object
    field: str
    policy: str
    reason: str
    monitor_sample_id: str = ""
    decision_id: str = ""
    observation_id: str = ""
    cause_id: Optional[str] = None
    action_effective_time_ns: Optional[float] = None
    pmg: Optional[int] = None
    details: Optional[Mapping[str, object]] = None

    def to_row(self) -> Dict[str, object]:
        return {
            "event_id": self.event_id,
            "time_ns": self.event_time_ns,
            "event_time_ns": self.event_time_ns,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "target_msc": self.resource_id,
            "partid": self.partid,
            "pmg": self.pmg,
            "event_type": self.event_type,
            "field": self.field,
            "old_state": self.old_state,
            "new_state": self.new_state,
            "old_value": self.old_state,
            "new_value": self.new_state,
            "policy": self.policy,
            "reason": self.reason,
            "monitor_sample_id": self.monitor_sample_id,
            "decision_id": self.decision_id,
            "observation_id": self.observation_id,
            "cause_id": self.cause_id,
            "action_effective_time_ns": self.action_effective_time_ns,
            "details": dict(self.details or {}),
        }
