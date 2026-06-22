from __future__ import annotations

import yaml

from src.config.loader import load_config
from src.sim.simulation import Simulation
from src.web.config_builder import build_config, default_parameters


def _run_single_thread(tmp_path, *, workload_type: str, dependency_mode: str):
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 60_000,
            "control_interval_ns": 20_000,
            "max_outstanding": 16,
            "core_max_outstanding": 16,
            "mc_base_latency_ns": 500,
            "l3_sets": 1024,
        }
    )
    for row in parameters["stimulus_configs"]:
        row["enabled"] = row["slot"] == 0
    parameters["stimulus_configs"][0].update(
        {
            "workload_type": workload_type,
            "address_pattern": (
                "pointer_chase"
                if dependency_mode == "pointer_chain"
                else "uniform_random"
            ),
            "dependency_mode": dependency_mode,
            "source_queue_depth": 16,
            "eligible_scan_depth": 16,
            "issue_selection": "eligible_scan",
            "independent_chains": 1,
            "rate_value": 500,
            "rate_unit": "mrps",
            "request_size_bytes": 64,
            "read_ratio": 1.0,
        }
    )
    raw = build_config(parameters, str(tmp_path / dependency_mode))
    path = tmp_path / f"{dependency_mode}.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return Simulation.from_config(load_config(path)).run()


def test_pointer_chain_waits_for_previous_response(tmp_path) -> None:
    result = _run_single_thread(
        tmp_path,
        workload_type="pointer_chase",
        dependency_mode="pointer_chain",
    )
    rows = [
        row for row in result.collector.timeline_rows
        if row["requester_id"] == "cpu0.t0"
    ]
    assert len(rows) > 3
    intervals = sorted(
        (
            float(row["time_ns"]) - float(row["total_latency_ns"]),
            float(row["time_ns"]),
        )
        for row in rows
    )
    previous_complete = -1.0
    for issue_time, complete_time in intervals:
        assert issue_time + 1e-9 >= previous_complete
        previous_complete = complete_time


def test_independent_stimulus_can_use_multiple_ostd(tmp_path) -> None:
    result = _run_single_thread(
        tmp_path,
        workload_type="random_read",
        dependency_mode="independent",
    )
    peaks = [
        row["peak_outstanding"]
        for row in result.collector.requester_rows
        if row["requester_id"] == "cpu0.t0"
    ]
    assert peaks
    assert max(peaks) > 1
