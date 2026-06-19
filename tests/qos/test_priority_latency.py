from __future__ import annotations

from src.config.loader import load_config
from src.sim.simulation import Simulation


def test_higher_priority_reduces_latency_under_contention(base_config, config_writer) -> None:
    base_config["mpam"]["msc_controls"] = [
        {
            "msc_id": "slc0",
            "controls": [
                {"partid": 1, "cache_portion_bitmap": "0"},
                {"partid": 2, "cache_portion_bitmap": "0"},
            ],
        },
        {
            "msc_id": "mc0",
            "controls": [
                {"partid": 1, "priority": 15},
                {"partid": 2, "priority": 1},
            ],
        },
    ]
    base_config["workloads"] = [
        {
            "name": "protected",
            "type": "random_read",
            "requesters": ["cpu0.t0"],
            "partid": 1,
            "pmg": 0,
            "request_size_bytes": 64,
            "injection_rate_gbps": 45,
            "read_ratio": 1.0,
            "working_set_bytes": 16_777_216,
        },
        {
            "name": "background",
            "type": "random_read",
            "requesters": ["cpu1.t0"],
            "partid": 2,
            "pmg": 0,
            "request_size_bytes": 64,
            "injection_rate_gbps": 45,
            "read_ratio": 1.0,
            "working_set_bytes": 16_777_216,
        },
    ]
    config = load_config(config_writer(base_config))
    result = Simulation.from_config(config).run()
    metrics = result.collector.cumulative_metrics(result.elapsed_ns)
    assert metrics[1]["p99_latency_ns"] < metrics[2]["p99_latency_ns"]
    assert metrics[1]["avg_mem_queue_delay_ns"] < metrics[2]["avg_mem_queue_delay_ns"]
