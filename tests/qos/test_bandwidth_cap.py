from __future__ import annotations

from src.config.loader import load_config
from src.sim.simulation import Simulation


def test_memory_controller_bandwidth_cap(base_config, config_writer) -> None:
    base_config["mpam"]["msc_controls"] = [
        {"msc_id": "slc0", "controls": [{"partid": 2, "cache_portion_bitmap": "0"}]},
        {"msc_id": "mc0", "controls": [{"partid": 2, "bw_max_gbps": 10, "priority": 4}]},
    ]
    base_config["workloads"] = [
        {
            "name": "bandwidth_hog",
            "type": "stream",
            "requesters": ["cpu0.t0"],
            "partid": 2,
            "pmg": 0,
            "request_size_bytes": 64,
            "injection_rate_gbps": 50,
            "read_ratio": 1.0,
            "working_set_bytes": 16_777_216,
        }
    ]
    config = load_config(config_writer(base_config))
    result = Simulation.from_config(config).run()
    metrics = result.collector.cumulative_metrics(result.elapsed_ns)[2]
    mc_row = next(
        row
        for row in reversed(result.collector.msc_rows)
        if row["msc_type"] == "memory_controller"
    )
    monitor = mc_row["per_partid"]["2"]
    assert 10.0 < metrics["throughput_gbps"] < 25.0
    assert monitor["hardlimit_block_events"] > 0
    assert monitor["throttle_delay_ns"] > 0
    assert metrics["avg_throttle_delay_ns"] > 0
