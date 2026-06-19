from __future__ import annotations

from src.config.loader import load_config
from src.sim.simulation import Simulation


def test_fixed_seed_is_deterministic(base_config, config_writer) -> None:
    base_config["workloads"] = [
        {
            "name": "random",
            "type": "random_read",
            "requesters": ["cpu0.t0"],
            "partid": 1,
            "pmg": 0,
            "request_size_bytes": 64,
            "injection_rate_gbps": 10,
            "read_ratio": 1.0,
            "working_set_bytes": 2_097_152,
            "injection": {"mode": "poisson", "rate_gbps": 10},
        }
    ]
    path = config_writer(base_config)
    first = Simulation.from_config(load_config(path)).run(30_000)
    second = Simulation.from_config(load_config(path)).run(30_000)
    assert first.collector.cumulative_metrics(first.elapsed_ns) == second.collector.cumulative_metrics(
        second.elapsed_ns
    )
