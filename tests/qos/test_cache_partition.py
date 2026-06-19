from __future__ import annotations

from copy import deepcopy

from src.config.loader import load_config
from src.sim.simulation import Simulation


def _run_with_mask(base_config, config_writer, mask: str, name: str):
    config_dict = deepcopy(base_config)
    config_dict["mpam"]["msc_controls"] = [
        {"msc_id": "slc0", "controls": [{"partid": 1, "cache_portion_bitmap": mask}]}
    ]
    config_dict["workloads"] = [
        {
            "name": "cache_workload",
            "type": "random_read",
            "requesters": ["cpu0.t0"],
            "partid": 1,
            "pmg": 0,
            "request_size_bytes": 64,
            "injection_rate_gbps": 20,
            "read_ratio": 1.0,
            "working_set_bytes": 1_048_576,
            "address_distribution": "random",
            "locality": "high",
        }
    ]
    config = load_config(config_writer(config_dict, name))
    result = Simulation.from_config(config).run()
    return result.collector.cumulative_metrics(result.elapsed_ns)[1]


def test_larger_cache_portion_improves_hit_rate(base_config, config_writer) -> None:
    small = _run_with_mask(base_config, config_writer, "1", "small.yaml")
    large = _run_with_mask(base_config, config_writer, "f", "large.yaml")
    assert large["cache_hit_rate"] > small["cache_hit_rate"]
    assert large["avg_latency_ns"] < small["avg_latency_ns"]
