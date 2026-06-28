from __future__ import annotations

from typing import Optional

from src.config.schema import (
    MPAMSettingConfig,
    MemoryControllerConfig,
)
from src.contracts.transaction import Transaction
from src.ddr.memctrl import MemoryControllerMSC
from src.mpam.settings import SettingsTable
from src.sim.kernel import SimulationKernel


def _request(
    transaction_id: int,
    partid: int,
    address: int,
    operation: str = "read",
) -> Transaction:
    request = Transaction(
        transaction_id=transaction_id,
        workload_name="mc-test",
        workload_type="random_read",
        requester_id=f"cpu0.t{partid % 2}",
        partid=partid,
        pmg=partid,
        address=address,
        size_bytes=64,
        operation=operation,
        issue_time_ns=0,
        working_set_bytes=4096,
        locality="medium",
        source_node="r0",
    )
    request.set_line_size(64)
    return request


def _mc(
    controls: list[MPAMSettingConfig],
    **overrides,
):
    kernel = SimulationKernel()
    completed = []
    config = MemoryControllerConfig(
        id="mc0",
        channels=1,
        bandwidth_gbps_per_channel=64,
        scheduler="priority_rr",
        queue_depth=8,
        base_latency_ns=0,
        clock_mhz=1000,
        monitor_period_cycles=8,
        history_weight=0,
        current_weight=1,
        **overrides,
    )
    mc = MemoryControllerMSC(
        kernel,
        config,
        SettingsTable(controls),
        completed.append,
    )
    return kernel, mc, completed


def _control(
    partid: int,
    *,
    qos: int = 0,
    bmin: Optional[float] = None,
    bmax: Optional[float] = None,
    mode: str = "softlimit",
) -> MPAMSettingConfig:
    return MPAMSettingConfig(
        partid=partid,
        bw_max_gbps=bmax,
        bw_min_gbps=bmin,
        bw_limit_mode=mode,
        mc_qos=qos,
        bmin_enable=bmin is not None,
        bmax_enable=bmax is not None,
    )


def test_full_buffer_candidate_can_beat_earlier_slot() -> None:
    _, mc, _ = _mc([_control(0, qos=0), _control(1, qos=7)])
    low = _request(1, 0, 0x0000)
    high = _request(2, 1, 0x1000)
    mc.receive(low)
    mc.receive(high)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request is high
    assert mc.queue_length == 1


def test_same_line_write_orders_but_read_read_can_reorder() -> None:
    _, write_mc, _ = _mc(
        [_control(0, qos=0), _control(1, qos=7)]
    )
    older_write = _request(1, 0, 0x2000, "write")
    newer_read = _request(2, 1, 0x2000, "read")
    write_mc.receive(older_write)
    write_mc.receive(newer_read)
    selected = write_mc._select_request()
    assert selected is not None
    assert selected.request is older_write

    _, read_mc, _ = _mc(
        [_control(0, qos=0), _control(1, qos=7)]
    )
    older_read = _request(3, 0, 0x3000, "read")
    newer_high_read = _request(4, 1, 0x3000, "read")
    read_mc.receive(older_read)
    read_mc.receive(newer_high_read)
    selected = read_mc._select_request()
    assert selected is not None
    assert selected.request is newer_high_read


def test_equal_qos_uses_rotating_buffer_slot() -> None:
    _, mc, _ = _mc([_control(0)])
    first = _request(1, 0, 0x0000)
    second = _request(2, 0, 0x1000)
    mc.receive(first)
    mc.receive(second)

    assert mc._select_request().request is first
    refill = _request(3, 0, 0x2000)
    mc.receive(refill)
    assert mc._select_request().request is second


def test_mc_qos_mapping_disabled_keeps_eight_level_ordering() -> None:
    _, mc, _ = _mc(
        [_control(0, qos=1), _control(1, qos=2)],
        qos_map_8_to_4_enable=False,
    )
    low = _request(1, 0, 0x0000)
    high = _request(2, 1, 0x1000)
    mc.receive(low)
    mc.receive(high)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request is high
    assert high.mc_arbitration.raw_effective_qos == 2
    assert high.mc_arbitration.effective_qos == 2
    assert high.mc_arbitration.qos_mapping_enabled is False


def test_mc_qos_mapping_enabled_collapses_to_four_level_ordering() -> None:
    _, mc, _ = _mc(
        [_control(0, qos=1), _control(1, qos=2)],
        qos_map_8_to_4_enable=True,
    )
    earlier = _request(1, 0, 0x0000)
    later_same_final = _request(2, 1, 0x1000)
    mc.receive(earlier)
    mc.receive(later_same_final)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request is earlier
    assert earlier.mc_arbitration.raw_effective_qos == 1
    assert earlier.mc_arbitration.effective_qos == 1
    assert mc._map_effective_qos(2) == 1
    assert earlier.mc_arbitration.qos_mapping_enabled is True


def test_mc_qos_mapping_exports_raw_and_final_qos_evidence() -> None:
    kernel, mc, _ = _mc(
        [_control(0, qos=6)],
        qos_map_8_to_4_enable=True,
    )
    mc.receive(_request(1, 0, 0x0000))

    kernel.run(0.0)
    snapshot = mc.monitor_snapshot(1.0)
    row = snapshot.payload["per_partid"]["0"]

    assert row["raw_effective_qos_avg"] == 6
    assert row["effective_qos_avg"] == 2
    assert row["qos_map_8_to_4_enable"] is True
    assert row["qos_mapping_events"] == 1


def test_fixed_step_qos_adjustment_keeps_configured_bmin_delta() -> None:
    _, mc, _ = _mc(
        [_control(0, qos=0, bmin=100), _control(1, qos=1)],
        qos_adjust_mode="fixed_step",
        bmin_qos_promote=2,
    )
    mc._under_bmin[0] = True
    promoted = _request(1, 0, 0x0000)
    other = _request(2, 1, 0x1000)
    mc.receive(promoted)
    mc.receive(other)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request is promoted
    assert promoted.mc_arbitration.qos_adjust_mode == "fixed_step"
    assert promoted.mc_arbitration.bmin_qos_delta == 2
    assert promoted.mc_arbitration.raw_effective_qos == 2


def test_error_weighted_bmax_uses_control_bandwidth_error() -> None:
    _, mc, _ = _mc(
        [_control(0, qos=7, bmax=100), _control(1, qos=4)],
        qos_adjust_mode="error_weighted",
        bmax_error_weight=4.0,
        qos_error_deadband_percent=5.0,
        qos_error_max_delta=3,
        qos_error_quantization="threshold_lut",
    )
    mc._over_bmax[0] = True
    mc._control_bandwidth_gbps[0] = 150.0
    over = _request(1, 0, 0x0000)
    other = _request(2, 1, 0x1000)
    mc.receive(over)
    mc.receive(other)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request is over
    assert over.mc_arbitration.qos_adjust_mode == "error_weighted"
    assert over.mc_arbitration.bmax_error_ratio == 0.5
    assert over.mc_arbitration.softlimit_qos_delta == 2
    assert over.mc_arbitration.raw_effective_qos == 5


def test_error_weighted_bmin_uses_control_bandwidth_error() -> None:
    _, mc, _ = _mc(
        [_control(0, qos=0, bmin=100), _control(1, qos=1)],
        qos_adjust_mode="error_weighted",
        bmin_error_weight=4.0,
        qos_error_deadband_percent=5.0,
        qos_error_max_delta=3,
        qos_error_quantization="threshold_lut",
    )
    mc._under_bmin[0] = True
    mc._control_bandwidth_gbps[0] = 50.0
    under = _request(1, 0, 0x0000)
    other = _request(2, 1, 0x1000)
    mc.receive(under)
    mc.receive(other)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request is under
    assert under.mc_arbitration.qos_adjust_mode == "error_weighted"
    assert under.mc_arbitration.bmin_error_ratio == 0.5
    assert under.mc_arbitration.bmin_qos_delta == 2
    assert under.mc_arbitration.raw_effective_qos == 2


def test_error_weighted_deadband_can_suppress_soft_delta() -> None:
    _, mc, _ = _mc(
        [_control(0, qos=4, bmax=100), _control(1, qos=3)],
        qos_adjust_mode="error_weighted",
        bmax_error_weight=4.0,
        qos_error_deadband_percent=5.0,
        qos_error_max_delta=3,
        qos_error_quantization="ceil",
    )
    mc._over_bmax[0] = True
    mc._control_bandwidth_gbps[0] = 103.0
    over = _request(1, 0, 0x0000)
    other = _request(2, 1, 0x1000)
    mc.receive(over)
    mc.receive(other)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request is over
    assert over.mc_arbitration.bmax_error_ratio == 0.03
    assert over.mc_arbitration.soft_over_limit is True
    assert over.mc_arbitration.soft_demoted is False
    assert over.mc_arbitration.softlimit_qos_delta == 0
    assert over.mc_arbitration.raw_effective_qos == 4


def _selected_over_qos(
    *,
    order: str,
    op: str,
) -> Transaction:
    _, mc, _ = _mc(
        [_control(0, qos=4, bmax=100), _control(1, qos=0)],
        qos_combiner_order=order,
        qos_combine_op=op,
        qos_adjust_mode="fixed_step",
        softlimit_qos_demote=3,
    )
    mc._over_bmax[0] = True
    over = _request(1, 0, 0x0000)
    over.qos_class = 7
    other = _request(2, 1, 0x1000)
    other.qos_class = 0
    mc.receive(over)
    mc.receive(other)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request is over
    assert over.mc_arbitration.request_qos == 7
    assert over.mc_arbitration.mpam_config_qos == 4
    assert over.mc_arbitration.mpam_adjust_qos == -3
    assert over.mc_arbitration.qos_combiner_order == order
    assert over.mc_arbitration.qos_combine_op == op
    return over


def test_mc_qos_combiner_replace_is_equivalent_across_orders() -> None:
    path1 = _selected_over_qos(
        order="adjust_before_request_combine",
        op="replace",
    )
    path2 = _selected_over_qos(
        order="adjust_after_request_combine",
        op="replace",
    )

    assert path1.mc_arbitration.raw_effective_qos == 1
    assert path2.mc_arbitration.raw_effective_qos == 1


def test_mc_qos_combiner_max_exposes_request_override_risk() -> None:
    path1 = _selected_over_qos(
        order="adjust_before_request_combine",
        op="max",
    )
    path2 = _selected_over_qos(
        order="adjust_after_request_combine",
        op="max",
    )

    assert path1.mc_arbitration.raw_effective_qos == 7
    assert path2.mc_arbitration.raw_effective_qos == 4


def test_mc_qos_combiner_average_keeps_path2_adjust_last() -> None:
    path1 = _selected_over_qos(
        order="adjust_before_request_combine",
        op="average",
    )
    path2 = _selected_over_qos(
        order="adjust_after_request_combine",
        op="average",
    )

    assert path1.mc_arbitration.raw_effective_qos == 4
    assert path2.mc_arbitration.raw_effective_qos == 2


def test_hard_bmax_uses_published_control_bandwidth_by_period() -> None:
    kernel, mc, _ = _mc(
        [_control(0, bmax=16, mode="hardlimit")]
    )
    for index in range(4):
        mc.receive(_request(index, 0, index * 0x1000))

    kernel.run(7.9)
    assert mc._hard_block[0] is False
    assert mc.queue_length == 3

    kernel.run(8.1)
    assert mc._raw_bandwidth_gbps[0] == 64
    assert mc._filtered_bandwidth_gbps[0] == 64
    assert mc._control_bandwidth_gbps[0] == 64
    assert mc._hard_block[0] is True
    assert mc.queue_length == 3
    blocked_depth = mc.queue_length

    kernel.run(15.9)
    assert mc._hard_block[0] is True
    assert mc.queue_length == blocked_depth

    kernel.run(16.1)
    assert mc._control_bandwidth_gbps[0] == 0
    assert mc._hard_block[0] is False
    assert mc.queue_length == blocked_depth - 1


def test_soft_bmax_without_partid_contention_stays_eligible() -> None:
    _, mc, _ = _mc(
        [_control(0, qos=4, bmax=1, mode="softlimit")]
    )
    request = _request(1, 0, 0)
    mc._over_bmax[0] = True
    mc.receive(request)

    selected = mc._select_request()

    assert selected is not None
    assert selected.request.mc_arbitration.soft_over_limit is True
    assert selected.request.mc_arbitration.soft_demoted is False
    assert selected.request.mc_arbitration.effective_qos == 4


def test_service_deficit_is_per_partid_saturating_state() -> None:
    _, mc, _ = _mc(
        [_control(0), _control(1)],
        aging_mode="per_partid_service_deficit",
        aging_counter_bits=2,
        aging_quantum_cycles=8,
        qos_aging_max_steps=2,
    )
    mc.receive(_request(1, 0, 0))
    mc.receive(_request(2, 1, 0x1000))

    for _ in range(5):
        mc._update_service_deficit()

    assert mc._service_deficit[0] == 3
    assert mc._service_deficit[1] == 3
    assert mc._deficit_qos_steps(0) == 2
    mc._grant_seen[0] = True
    mc._update_service_deficit()
    assert mc._service_deficit[0] == 2
