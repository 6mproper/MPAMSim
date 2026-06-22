from src.contracts.telemetry import ControlDecision


# Compatibility import for policy modules created before the typed contract.
ControlUpdate = ControlDecision

__all__ = ["ControlDecision", "ControlUpdate"]
