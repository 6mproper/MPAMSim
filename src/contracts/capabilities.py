from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Protocol, Tuple


@dataclass(frozen=True)
class CapabilityDescriptor:
    component_id: str
    component_type: str
    schema_version: str
    inputs: Tuple[str, ...]
    outputs: Tuple[str, ...]
    capabilities: Tuple[str, ...]
    required_monitors: Tuple[str, ...]
    actions: Tuple[str, ...]
    validation_hooks: Tuple[str, ...]
    incompatible_capabilities: Tuple[str, ...] = ()
    approximations: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class CapabilityProvider(Protocol):
    @property
    def capability_descriptor(self) -> CapabilityDescriptor:
        ...


class ComponentRegistry:
    def __init__(self) -> None:
        self._components: Dict[str, CapabilityDescriptor] = {}

    def register(self, component: CapabilityProvider) -> None:
        descriptor = component.capability_descriptor
        if descriptor.component_id in self._components:
            raise ValueError(
                f"Duplicate component id: {descriptor.component_id}"
            )
        self._components[descriptor.component_id] = descriptor

    def register_all(
        self,
        components: Iterable[CapabilityProvider],
    ) -> None:
        for component in components:
            self.register(component)
        self.validate()

    def validate(self) -> None:
        active_capabilities = {
            capability
            for descriptor in self._components.values()
            for capability in descriptor.capabilities
        }
        errors: List[str] = []
        for descriptor in self._components.values():
            conflicts = (
                set(descriptor.incompatible_capabilities)
                & active_capabilities
            )
            if conflicts:
                errors.append(
                    "{} conflicts with {}".format(
                        descriptor.component_id,
                        ", ".join(sorted(conflicts)),
                    )
                )
        if errors:
            raise ValueError(
                "Incompatible component capabilities: "
                + "; ".join(errors)
            )

    def descriptors(self) -> Tuple[CapabilityDescriptor, ...]:
        return tuple(
            self._components[key]
            for key in sorted(self._components)
        )

    def to_dicts(self) -> List[Dict[str, object]]:
        return [
            descriptor.to_dict()
            for descriptor in self.descriptors()
        ]
