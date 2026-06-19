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
    assert cache_row["per_partid"]["2"]["cmax"] == 16
    assert cache_row["per_partid"]["2"]["enforcement_enabled"] is False
    assert mc_row["per_partid"]["2"]["limit_mode"] == "disabled"
    assert mc_row["per_partid"]["2"]["hardlimit_block_events"] == 0
