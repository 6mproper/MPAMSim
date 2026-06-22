from __future__ import annotations

from src.config.schema import NocConfig
from src.contracts.transaction import Transaction
from src.noc.fabric import CallbackEndpoint, NocFabric
from src.sim.kernel import SimulationKernel


def _config(
    slots: int = 1,
    flit_bytes: int = 16,
    tie_direction: str = "cw",
) -> NocConfig:
    return NocConfig(
        topology="three_bidirectional_bufferless_rings",
        routers=4,
        link_bandwidth_gbps=256,
        router_latency_ns=1,
        queue_depth=1,
        virtual_channels=1,
        average_hops=1,
        clock_mhz=1000,
        flit_bytes=flit_bytes,
        link_slots_per_direction=slots,
        hop_latency_cycles=1,
        tie_direction=tie_direction,
    )


def _transaction(
    transaction_id: int = 1,
    size_bytes: int = 64,
) -> Transaction:
    return Transaction(
        transaction_id=transaction_id,
        workload_name="ring-test",
        workload_type="stream",
        requester_id="cpu0.t0",
        partid=1,
        pmg=0,
        address=0,
        size_bytes=size_bytes,
        operation="read",
        issue_time_ns=0,
        working_set_bytes=4096,
        locality="low",
        source_node="r0",
    )


def test_shortest_path_and_tie_direction_are_deterministic() -> None:
    kernel = SimulationKernel()
    clockwise = NocFabric(
        kernel,
        _config(tie_direction="cw"),
        ("r0", "r1", "r2", "r3"),
    )
    counter_clockwise = NocFabric(
        kernel,
        _config(tie_direction="ccw"),
        ("r0", "r1", "r2", "r3"),
    )

    assert clockwise.route_direction("r0", "r1") == "cw"
    assert clockwise.route_direction("r0", "r3") == "ccw"
    assert clockwise.route_direction("r0", "r2") == "cw"
    assert counter_clockwise.route_direction("r0", "r2") == "ccw"


def test_full_source_link_backpressures_without_buffering() -> None:
    kernel = SimulationKernel()
    ring = NocFabric(
        kernel,
        _config(slots=1),
        ("r0", "r1", "r2", "r3"),
    )
    assert ring.transmit(
        _transaction(1),
        "req",
        CallbackEndpoint(lambda _request: None),
        source_node="r0",
        destination_node="r2",
    )
    assert not ring.can_inject("r0", "r2", "req")
    assert not ring.transmit(
        _transaction(2),
        "req",
        CallbackEndpoint(lambda _request: None),
        source_node="r0",
        destination_node="r2",
    )
    assert ring.in_flight_flits == 1


def test_rejected_ejection_recirculates_until_endpoint_ready() -> None:
    kernel = SimulationKernel()
    ring = NocFabric(
        kernel,
        _config(),
        ("r0", "r1", "r2", "r3"),
    )
    completed = []
    endpoint = CallbackEndpoint(
        completed.append,
        readiness=lambda _request: kernel.now_ns >= 5.0,
    )
    request = _transaction()

    assert ring.transmit(
        request,
        "req",
        endpoint,
        source_node="r0",
        destination_node="r1",
    )
    kernel.run(5.0)

    assert completed == [request]
    snapshot = ring.monitor_snapshot(5.0).payload
    assert snapshot["failed_ejections"] == 1
    assert snapshot["full_laps"] == 1
    assert snapshot["in_flight_flits"] == 0
    assert snapshot["per_node"]["r1"]["failed_ejections"] == 1
    assert snapshot["per_link"]["req:cw:link0"]["hops"] >= 1
    assert (
        snapshot["per_partid_channel_direction"]["1:req:cw"][
            "failed_ejections"
        ]
        == 1
    )
    assert request.timing.req_ring_delay_ns == 5.0


def test_dat_flits_inject_independently_and_complete_after_reassembly() -> None:
    kernel = SimulationKernel()
    ring = NocFabric(
        kernel,
        _config(slots=1, flit_bytes=16),
        ("r0", "r1", "r2", "r3"),
    )
    completed = []
    request = _transaction(size_bytes=64)

    assert ring.transmit(
        request,
        "dat",
        CallbackEndpoint(completed.append),
        source_node="r0",
        destination_node="r1",
    )
    kernel.run(3.0)
    assert completed == []
    kernel.run(4.0)

    assert completed == [request]
    snapshot = ring.monitor_snapshot(4.0).payload
    assert snapshot["injected_flits"] == 4
    assert snapshot["ejected_flits"] == 4
    assert snapshot["completed_transfers"] == 1
    assert request.timing.rsp_dat_ring_delay_ns == 4.0


def test_completion_callback_can_inject_next_transfer_safely() -> None:
    kernel = SimulationKernel()
    ring = NocFabric(
        kernel,
        _config(),
        ("r0", "r1", "r2", "r3"),
    )
    completed = []
    second = _transaction(2)

    def first_complete(request: Transaction) -> None:
        completed.append(request.transaction_id)
        assert ring.transmit(
            second,
            "req",
            CallbackEndpoint(
                lambda item: completed.append(item.transaction_id)
            ),
            source_node="r1",
            destination_node="r2",
        )

    assert ring.transmit(
        _transaction(1),
        "req",
        CallbackEndpoint(first_complete),
        source_node="r0",
        destination_node="r1",
    )
    kernel.run(2.0)

    assert completed == [1, 2]
