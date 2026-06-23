from __future__ import annotations

from dataclasses import dataclass

import pytest
import yaml

from src.contracts.capabilities import (
    CapabilityDescriptor,
    ComponentRegistry,
)
from src.contracts.telemetry import (
    ControlContext,
    ControlDecision,
    ControlEvent,
    ControlOutcome,
    MetricSemantic,
    MonitorSnapshot,
)
from src.contracts.transaction import (
    Operation,
    RequestClass,
    Transaction,
)
from src.config.loader import load_config
from src.sim.simulation import Simulation
from src.traffic.request import Request
from src.web.config_builder import build_config, default_parameters


def make_transaction() -> Transaction:
    return Transaction(
        transaction_id=7,
        workload_name="typed",
        workload_type="random_read",
        requester_id="cpu0.t1",
        core_id="cpu0",
        thread_id=1,
        partid=3,
        pmg=2,
        address=0x1234,
        size_bytes=64,
        operation=Operation.READ,
        issue_time_ns=10.0,
        working_set_bytes=1 << 20,
        locality="medium",
        source_node="r0",
    )


def descriptor(
    component_id: str,
    capabilities: tuple = (),
    incompatible: tuple = (),
) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        component_id=component_id,
        component_type="test",
        schema_version="1.0",
        inputs=("Transaction",),
        outputs=("MonitorSnapshot",),
        capabilities=capabilities,
        required_monitors=(),
        actions=(),
        validation_hooks=(),
        incompatible_capabilities=incompatible,
    )


@dataclass
class Provider:
    capability_descriptor: CapabilityDescriptor


def test_request_is_the_single_transaction_runtime_type() -> None:
    transaction = make_transaction()

    assert Request is Transaction
    assert isinstance(transaction, Request)
    assert transaction.request_id == 7
    assert transaction.addr == 0x1234
    assert transaction.op == "read"
    assert transaction.request_class == RequestClass.DEMAND_READ


def test_transaction_rejects_undeclared_dynamic_fields() -> None:
    transaction = make_transaction()

    with pytest.raises(
        AttributeError,
        match="Transaction field is not declared",
    ):
        transaction._mc_effective_qos = 7


def test_transaction_owns_route_timing_and_mc_decision() -> None:
    transaction = make_transaction()
    transaction.cache_id = "slc0"
    transaction.memory_controller_id = "mc1"
    transaction.destination_node = "mc1"
    transaction.set_line_size(64)
    transaction.noc_delay_ns += 3.0
    transaction.cache_delay_ns += 5.0
    transaction.mem_service_delay_ns += 11.0
    transaction.mc_arbitration.base_qos = 3
    transaction.mc_arbitration.effective_qos = 6
    transaction.mark_complete(29.0)

    assert transaction.line_address == 0x1200
    assert transaction.route.cache_id == "slc0"
    assert transaction.route.memory_controller_id == "mc1"
    assert transaction.total_latency_ns == 19.0
    assert transaction.mc_arbitration.effective_qos == 6
    assert transaction.timing.completion_time_ns == 29.0


def test_monitor_snapshot_flattens_partid_and_group_samples() -> None:
    snapshot = MonitorSnapshot.from_payload(
        time_ns=256.0,
        resource_type="cache",
        resource_id="slc0",
        interval_ns=256.0,
        sample_id="slc0:sample:1",
        payload={
            "utilization": 0.5,
            "per_partid": {
                "3": {
                    "configured_cmax_percent": 25.0,
                    "control_occupancy_bytes": 2048,
                    "filtered_occupancy_bytes": 4096,
                    "occupancy_share": 0.20,
                }
            },
            "monitor_groups": {
                "3:2": {
                    "partid": 3,
                    "pmg": 2,
                    "estimated_occupancy_bytes": 4096,
                }
            },
        },
    )

    rows = [sample.to_row() for sample in snapshot.samples]
    assert rows[0]["sample_id"] == "slc0:sample:1"
    assert rows[0]["semantic"] == MetricSemantic.RAW_MONITOR.value
    configured = next(
        row
        for row in rows
        if row["metric"] == "configured_cmax_percent"
    )
    group = next(
        row
        for row in rows
        if row["metric"] == "estimated_occupancy_bytes"
    )
    control_input = next(
        row
        for row in rows
        if row["metric"] == "control_occupancy_bytes"
    )
    filtered = next(
        row
        for row in rows
        if row["metric"] == "filtered_occupancy_bytes"
    )

    assert configured["partid"] == 3
    assert configured["semantic"] == (
        MetricSemantic.CONFIGURED_TARGET.value
    )
    assert group["partid"] == 3
    assert group["pmg"] == 2
    assert group["unit"] == "byte"
    assert control_input["semantic"] == MetricSemantic.CONTROL_INPUT.value
    assert filtered["semantic"] == MetricSemantic.FILTERED_MONITOR.value


def test_control_decision_and_event_keep_causal_ids() -> None:
    decision = ControlDecision(
        target_resource_id="mc0",
        partid=1,
        field="mc_qos",
        value=7,
        reason="P99 violation",
        policy="closed_loop_qos",
    ).with_context(
        decision_id="decision:2:closed_loop_qos:0",
        monitor_sample_id="interval:2",
        action_effective_time_ns=100_000.0,
    )
    event = ControlEvent(
        event_id="control-event:1",
        event_time_ns=100_000.0,
        resource_type="memory_controller",
        resource_id=decision.target_resource_id,
        partid=decision.partid,
        event_type="setting_applied",
        old_state=6,
        new_state=decision.value,
        field=decision.field,
        policy=decision.policy,
        reason=decision.reason,
        monitor_sample_id=decision.monitor_sample_id,
        decision_id=decision.decision_id,
        action_effective_time_ns=(
            decision.action_effective_time_ns
        ),
        outcome_state="met",
        outcome_reason="setting applied",
    )

    row = event.to_row()
    assert row["target_msc"] == "mc0"
    assert row["old_value"] == 6
    assert row["new_value"] == 7
    assert row["monitor_sample_id"] == "interval:2"
    assert row["decision_id"] == decision.decision_id
    assert row["outcome_state"] == "met"
    assert row["outcome_reason"] == "setting applied"


def test_control_outcome_and_context_are_typed_contracts() -> None:
    sample = MonitorSnapshot.from_payload(
        time_ns=8.0,
        resource_type="memory_controller",
        resource_id="mc0",
        interval_ns=8.0,
        sample_id="mc0:sample:1",
        payload={
            "per_partid": {
                "0": {
                    "control_bandwidth_gbps": 64.0,
                }
            }
        },
    ).samples[-1]
    outcome = ControlOutcome(
        target_state="overshoot",
        reason="BMAX exceeded before next control window",
        monitor_sample_id=sample.sample_id,
        metrics={"control_bandwidth_gbps": 64.0},
    )
    context = ControlContext(
        interval_index=1,
        time_ns=8.0,
        monitor_samples=(sample,),
        metrics_by_partid={0: {"control_bandwidth_gbps": 64.0}},
        authorized_inputs=("control_bandwidth_gbps",),
        action_effective_time_ns=16.0,
    )

    assert sample.semantic == MetricSemantic.CONTROL_INPUT
    assert outcome.to_dict()["target_state"] == "overshoot"
    assert context.authorized_inputs == ("control_bandwidth_gbps",)


def test_component_registry_rejects_duplicates_and_conflicts() -> None:
    registry = ComponentRegistry()
    registry.register(
        Provider(descriptor("a", capabilities=("cap_a",)))
    )
    with pytest.raises(ValueError, match="Duplicate component id"):
        registry.register(Provider(descriptor("a")))

    conflict = ComponentRegistry()
    conflict.register(
        Provider(
            descriptor(
                "a",
                capabilities=("cap_a",),
                incompatible=("cap_b",),
            )
        )
    )
    conflict.register(
        Provider(descriptor("b", capabilities=("cap_b",)))
    )
    with pytest.raises(
        ValueError,
        match="Incompatible component capabilities",
    ):
        conflict.validate()


def test_simulation_exports_resolvable_control_causality(
    tmp_path,
) -> None:
    parameters = default_parameters()
    parameters["duration_ns"] = 20_000
    parameters["control_interval_ns"] = 5_000
    parameters["min_hold_intervals"] = 1
    for row in parameters["stimulus_configs"][2:]:
        row["enabled"] = False
    parameters["stimulus_configs"][1]["target_p99_ns"] = 1
    raw = build_config(parameters, str(tmp_path / "run"))
    config_path = tmp_path / "typed.yaml"
    config_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )

    result = Simulation.from_config(load_config(config_path)).run()

    sample_ids = {
        row["sample_id"]
        for row in result.collector.monitor_sample_rows
    }
    applied = [
        event
        for event in result.collector.control_events
        if event.event_type == "setting_applied"
    ]
    assert applied
    assert all(event.decision_id for event in applied)
    assert all(
        event.monitor_sample_id in sample_ids
        for event in applied
    )
    assert {
        row["component_id"]
        for row in result.component_capabilities
    } >= {"noc", "slc0", "mc0"}
