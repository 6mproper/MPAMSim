from __future__ import annotations

from src.config.loader import load_config
from src.sim.simulation import Simulation


def test_static_report_is_generated(base_config, config_writer, tmp_path) -> None:
    base_config["workloads"] = [
        {
            "name": "small",
            "type": "stream",
            "requesters": ["cpu0.t0"],
            "partid": 1,
            "pmg": 0,
            "request_size_bytes": 64,
            "injection_rate_gbps": 5,
            "read_ratio": 1.0,
            "working_set_bytes": 1_048_576,
        }
    ]
    config = load_config(config_writer(base_config))
    result = Simulation.from_config(config).run(20_000)
    output = result.export(str(tmp_path / "run"))
    report = output / "report.html"
    assert report.exists()
    assert (output / "monitor_samples.csv").exists()
    assert (output / "control_events.csv").exists()
    assert (output / "component_capabilities.json").exists()
    text = report.read_text(encoding="utf-8")
    assert "Modeled Flow" in text
    assert "P99 latency over time" in text
