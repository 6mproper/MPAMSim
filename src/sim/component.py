from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Tuple

from src.contracts.capabilities import CapabilityDescriptor
from src.contracts.telemetry import MonitorSnapshot


class Component(ABC):
    schema_version = "1.0"
    inputs: Tuple[str, ...] = ("Transaction",)
    outputs: Tuple[str, ...] = ("Transaction", "MonitorSnapshot")
    capabilities: Tuple[str, ...] = ()
    required_monitors: Tuple[str, ...] = ()
    actions: Tuple[str, ...] = ()
    validation_hooks: Tuple[str, ...] = ()
    incompatible_capabilities: Tuple[str, ...] = ()
    approximations: Tuple[str, ...] = ()

    def __init__(
        self,
        component_id: str,
        component_type: str,
    ) -> None:
        self.component_id = component_id
        self.component_type = component_type
        self._monitor_sequence = 0

    @property
    def capability_descriptor(self) -> CapabilityDescriptor:
        return CapabilityDescriptor(
            component_id=self.component_id,
            component_type=self.component_type,
            schema_version=self.schema_version,
            inputs=self.inputs,
            outputs=self.outputs,
            capabilities=self.capabilities,
            required_monitors=self.required_monitors,
            actions=self.actions,
            validation_hooks=self.validation_hooks,
            incompatible_capabilities=self.incompatible_capabilities,
            approximations=self.approximations,
        )

    def build_monitor_snapshot(
        self,
        time_ns: float,
        interval_ns: float,
        payload: dict,
        local_cycle: int = None,
    ) -> MonitorSnapshot:
        self._monitor_sequence += 1
        return MonitorSnapshot.from_payload(
            time_ns=time_ns,
            resource_type=self.component_type,
            resource_id=self.component_id,
            interval_ns=interval_ns,
            sample_id=(
                f"{self.component_id}:sample:{self._monitor_sequence}"
            ),
            payload=payload,
            local_cycle=local_cycle,
        )

    @abstractmethod
    def monitor_snapshot(self, interval_ns: float) -> MonitorSnapshot:
        raise NotImplementedError
