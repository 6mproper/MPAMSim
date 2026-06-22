from __future__ import annotations

import yaml

from src.config.loader import load_config
from src.sim.simulation import Simulation
from src.web.config_builder import build_config, default_parameters


def test_l3_queue_reports_pressure_and_backpressure(tmp_path) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "duration_ns": 30_000,
            "control_interval_ns": 10_000,
            "l3_hit_latency_ns": 80,
            "l3_queue_depth": 4,
            "l3_lookup_parallelism": 1,
            "max_outstanding": 32,
            "noc_flit_bytes": 64,
            "noc_link_slots_per_direction": 64,
        }
    )
    for row in parameters["stimulus_configs"]:
        row["enabled"] = row["slot"] == 0
    parameters["stimulus_configs"][0].update(
        {
            "rate_value": 200,
            "rate_unit": "gbps",
            "request_size_bytes": 64,
        }
    )
    raw = build_config(parameters, str(tmp_path / "l3_queue"))
    path = tmp_path / "l3_queue.yaml"
    path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )

    result = Simulation.from_config(load_config(path)).run()
    rows = [
        row
        for row in result.collector.msc_rows
        if row["msc_type"] == "cache"
    ]

    assert max(row["queue_peak"] for row in rows) == 4
    assert any(row["queue_occupancy"] > 0 for row in rows)
    assert sum(
        row["per_partid"]["0"]["queue_full_events"]
        for row in rows
    ) > 0
    assert sum(
        row["per_partid"]["0"]["queue_delay_ns"]
        for row in rows
    ) > 0
