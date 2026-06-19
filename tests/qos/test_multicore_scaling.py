from __future__ import annotations

from src.config.loader import load_config
from src.sim.simulation import Simulation


def _run(base_config, config_writer, requesters, name):
    base_config["workloads"] = [
        {
            "name": "per_core_stream",
            "type": "stream",
            "requesters": requesters,
            "partid": 1,
            "pmg": 0,
            "request_size_bytes": 64,
            "injection_rate_gbps": 5,
            "injection_scope": "per_requester",
            "read_ratio": 1.0,
            "working_set_bytes": 16_777_216,
        }
    ]
    config = load_config(config_writer(base_config, name))
    result = Simulation.from_config(config).run(50_000)
    return result.collector.cumulative_metrics(result.elapsed_ns)[1]["throughput_gbps"]


def test_per_requester_rate_scales_with_active_cores(base_config, config_writer) -> None:
    one_core = _run(base_config, config_writer, ["cpu0.t0"], "one.yaml")
    two_cores = _run(base_config, config_writer, ["cpu0.t0", "cpu1.t0"], "two.yaml")
    assert two_cores > one_core * 1.7
