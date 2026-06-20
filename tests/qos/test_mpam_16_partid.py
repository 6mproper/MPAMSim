from __future__ import annotations

from src.config.loader import load_config
from src.sim.simulation import Simulation
from src.web.config_builder import build_config, default_parameters

import yaml


def test_l3_sample_monitor_reports_16_partids(tmp_path) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 50_000,
            "control_interval_ns": 10_000,
            "l3_sets": 1024,
            "l3_ways": 8,
        }
    )
    rows = parameters["partid_configs"]
    full_mask = "ff"
    for row in rows:
        row.update({"cpbm": full_mask, "cmin": 0, "cmax": 8})
    raw = build_config(parameters, str(tmp_path / "run"))
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    result = Simulation.from_config(load_config(path)).run()

    cache_rows = [
        row for row in result.collector.msc_rows
        if row["msc_type"] == "cache"
    ]
    assert cache_rows
    latest = cache_rows[-1]
    assert latest["sets"] == 1024
    assert latest["ways_per_set"] == 8
    assert latest["monitor_group_sets"] == 8
    assert len(latest["per_partid"]) == 16
    assert latest["per_partid"]["5"]["estimated_access_bytes"] >= 0
    assert latest["per_partid"]["11"]["cpbm"] == "ff"


def test_softlimit_is_work_conserving_but_hardlimit_caps(tmp_path) -> None:
    base = default_parameters()
    base.update(
        {
            "duration_ns": 100_000,
            "control_interval_ns": 20_000,
            "policy": "static_mpam",
        }
    )

    def run(mode: str, name: str):
        parameters = default_parameters()
        parameters.update(base)
        for row in parameters["stimulus_configs"]:
            row["enabled"] = row["slot"] == 2
        parameters["stimulus_configs"][2].update(
            {
                "rate_value": 40,
                "rate_unit": "gbps",
                "request_size_bytes": 64,
            }
        )
        parameters["partid_configs"][2].update(
            {
                "bmin_gbps": 0,
                "bmax_gbps": 10,
                "limit_mode": mode,
                "cpbm": "0000",
                "cmin": 0,
                "cmax": 0,
            }
        )
        raw = build_config(parameters, str(tmp_path / name))
        path = tmp_path / f"{name}.yaml"
        path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
        result = Simulation.from_config(load_config(path)).run()
        metrics = result.collector.cumulative_metrics(result.elapsed_ns)[2]
        mc_rows = [
            row for row in result.collector.msc_rows
            if row["msc_type"] == "memory_controller"
        ]
        return metrics, mc_rows[-1]["per_partid"]["2"]

    hard_metrics, hard_monitor = run("hardlimit", "hard")
    soft_metrics, soft_monitor = run("softlimit", "soft")
    assert hard_metrics["throughput_gbps"] <= 22.0
    assert soft_metrics["throughput_gbps"] > hard_metrics["throughput_gbps"] * 1.5
    assert hard_monitor["hardlimit_block_events"] > 0
    assert soft_monitor["softlimit_requests"] > 0


def test_no_control_keeps_16_monitors_without_enforcement(tmp_path) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 30_000,
            "control_interval_ns": 10_000,
            "policy": "no_control",
        }
    )
    parameters["partid_configs"][2].update(
        {
            "bmax_gbps": 1,
            "limit_mode": "hardlimit",
            "cmin": 0,
            "cmax": 0,
            "cpbm": "0000",
        }
    )
    raw = build_config(parameters, str(tmp_path / "no_control"))
    path = tmp_path / "no_control.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    simulation = Simulation.from_config(load_config(path))
    assert simulation._default_priority(1) == 0
    result = simulation.run()

    cache_row = next(
        row for row in reversed(result.collector.msc_rows)
        if row["msc_type"] == "cache"
    )
    mc_row = next(
        row for row in reversed(result.collector.msc_rows)
        if row["msc_type"] == "memory_controller"
    )
    assert len(cache_row["per_partid"]) == 16
    assert len(mc_row["per_partid"]) == 16
    assert cache_row["per_partid"]["2"]["cmax_percent"] == 100
    assert cache_row["per_partid"]["2"]["enforcement_enabled"] is False
    assert mc_row["per_partid"]["2"]["limit_mode"] == "disabled"
    assert mc_row["per_partid"]["2"]["hardlimit_block_events"] == 0


def test_monitor_groups_report_partid_pmg_utilization(tmp_path) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 30_000,
            "control_interval_ns": 10_000,
        }
    )
    for row in parameters["stimulus_configs"]:
        row["enabled"] = row["slot"] == 0
    parameters["stimulus_configs"][0].update(
        {
            "partid": 3,
            "pmg": 7,
            "rate_value": 20,
            "rate_unit": "gbps",
        }
    )
    raw = build_config(parameters, str(tmp_path / "groups"))
    path = tmp_path / "groups.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    result = Simulation.from_config(load_config(path)).run()

    cache_group = next(
        row["monitor_groups"]["3:7"]
        for row in reversed(result.collector.msc_rows)
        if row["msc_type"] == "cache"
        and "3:7" in row["monitor_groups"]
    )
    mc_group = next(
        row["monitor_groups"]["3:7"]
        for row in reversed(result.collector.msc_rows)
        if row["msc_type"] == "memory_controller"
        and "3:7" in row["monitor_groups"]
    )
    assert cache_group["partid"] == 3
    assert cache_group["pmg"] == 7
    assert 0 <= cache_group["occupancy_rate"] <= 1
    assert cache_group["allowed_capacity_bytes"] > 0
    assert mc_group["achieved_bandwidth_gbps"] > 0
    assert 0 <= mc_group["bandwidth_utilization"] <= 1
    assert mc_group["controller_bandwidth_gbps"] == 256


def test_cpu_monitor_reports_outstanding_by_partid(tmp_path) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 40_000,
            "control_interval_ns": 20_000,
            "max_outstanding": 4,
        }
    )
    for row in parameters["stimulus_configs"]:
        row["enabled"] = row["slot"] == 0
    parameters["stimulus_configs"][0].update(
        {
            "partid": 5,
            "pmg": 3,
            "workload_type": "pointer_chase",
            "rate_value": 100,
            "rate_unit": "mrps",
        }
    )

    raw = build_config(parameters, str(tmp_path / "cpu_monitor"))
    path = tmp_path / "cpu_monitor.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    result = Simulation.from_config(load_config(path)).run()

    rows = [
        row
        for row in result.collector.requester_rows
        if row["requester_id"] == "cpu0.t0"
        and row["partid"] == 5
    ]
    assert len(rows) == 2
    assert all(row["max_outstanding"] == 4 for row in rows)
    assert all(
        0 <= row["outstanding"] <= row["peak_outstanding"] <= 4
        for row in rows
    )
    assert rows[-1]["issued"] >= rows[-1]["completed"]
    assert rows[-1]["backpressure_ns"] >= 0


def test_independent_control_switches_report_neutral_effective_values(
    tmp_path,
) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 20_000,
            "control_interval_ns": 10_000,
            "l3_sets": 1024,
        }
    )
    for row in parameters["stimulus_configs"]:
        row["enabled"] = row["slot"] == 0
    parameters["stimulus_configs"][0]["partid"] = 2
    parameters["partid_configs"][2].update(
        {
            "cpbm": "00ff",
            "cmax": 1,
            "cmax_enable": False,
            "bmax_gbps": 1,
            "bmax_enable": False,
            "mc_qos": 7,
            "mc_qos_enable": False,
        }
    )

    raw = build_config(parameters, str(tmp_path / "switches"))
    path = tmp_path / "switches.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    result = Simulation.from_config(load_config(path)).run()

    cache_row = next(
        row
        for row in result.collector.msc_rows
        if row["msc_type"] == "cache"
    )["per_partid"]["2"]
    mc_row = next(
        row
        for row in result.collector.msc_rows
        if row["msc_type"] == "memory_controller"
    )["per_partid"]["2"]
    assert cache_row["configured_cmax"] == 1
    assert cache_row["cmax_enable"] is False
    assert cache_row["cmax_percent"] == 50
    assert mc_row["configured_bmax_gbps"] == 1
    assert mc_row["bmax_enable"] is False
    assert mc_row["bmax_gbps"] is None
    assert mc_row["configured_mc_qos"] == 7
    assert mc_row["mc_qos_enable"] is False
    assert mc_row["base_qos"] == 0


def test_cbusy_and_bmax_can_be_isolated_and_combined(tmp_path) -> None:
    def run(mode: str):
        parameters = default_parameters()
        parameters.update(
            {
                "duration_ns": 60_000,
                "control_interval_ns": 10_000,
                "memory_controllers": 1,
                "channels_per_mc": 1,
                "channel_bandwidth_gbps": 16,
                "mc_base_latency_ns": 300,
                "mc_queue_depth": 32,
                "max_outstanding": 32,
                "policy": "static_mpam",
                "cbusy_sample_ns": 500,
                "cbusy_feedback_latency_ns": 10,
                "cbusy_release_hold_samples": 3,
                "cbusy_l1_queue_ratio": 0.03,
                "cbusy_l2_queue_ratio": 0.06,
                "cbusy_l3_queue_ratio": 0.10,
            }
        )
        for row in parameters["stimulus_configs"]:
            row["enabled"] = row["slot"] == 0
        parameters["stimulus_configs"][0].update(
            {
                "partid": 0,
                "rate_value": 500,
                "rate_unit": "mrps",
                "workload_type": "random_read",
            }
        )
        parameters["partid_configs"][0].update(
            {
                "bmax_enable": mode in {"bmax", "combined"},
                "bmax_gbps": 8,
                "limit_mode": "hardlimit",
                "bmin_enable": False,
                "mc_qos_enable": False,
                "cbusy_enable": mode in {"cbusy", "combined"},
                "cbusy_l1_ostd": 8,
                "cbusy_l2_ostd": 4,
                "cbusy_l3_ostd": 2,
            }
        )
        raw = build_config(parameters, str(tmp_path / mode))
        path = tmp_path / f"{mode}.yaml"
        path.write_text(
            yaml.safe_dump(raw, sort_keys=False),
            encoding="utf-8",
        )
        result = Simulation.from_config(load_config(path)).run()
        mc_rows = [
            row
            for row in result.collector.msc_rows
            if row["msc_type"] == "memory_controller"
        ]
        cpu = [
            row
            for row in result.collector.requester_rows
            if row["partid"] == 0
        ][-1]
        return {
            "queue_peak": max(
                row["queue_occupancy"] for row in mc_rows
            ),
            "hard_blocks": sum(
                row["per_partid"]["0"]["hardlimit_block_events"]
                for row in mc_rows
            ),
            "cbusy_stall": cpu["cbusy_stall_ns"],
            "effective_ostd": cpu["effective_max_outstanding"],
            "cbusy_transitions": cpu["cbusy_transitions"],
            "cbusy_trace_events": sum(
                row["policy"] == "mc_cbusy"
                for row in result.collector.control_rows
            ),
        }

    baseline = run("none")
    bmax = run("bmax")
    cbusy = run("cbusy")
    combined = run("combined")

    assert baseline["hard_blocks"] == 0
    assert baseline["cbusy_stall"] == 0
    assert bmax["hard_blocks"] > 0
    assert bmax["cbusy_stall"] == 0
    assert cbusy["hard_blocks"] == 0
    assert cbusy["cbusy_stall"] > 0
    assert cbusy["effective_ostd"] < 32
    assert cbusy["cbusy_transitions"] > 0
    assert cbusy["cbusy_trace_events"] > 0
    assert cbusy["queue_peak"] < baseline["queue_peak"]
    assert combined["hard_blocks"] > 0
    assert combined["cbusy_stall"] > 0
    assert combined["queue_peak"] < bmax["queue_peak"]
