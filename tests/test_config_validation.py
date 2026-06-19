from __future__ import annotations

import pytest

from src.config.loader import load_config
from src.config.validator import ConfigError


def test_baseline_config_is_valid() -> None:
    config = load_config("examples/baseline_soc.yaml")
    assert len(config.requesters) == 32
    assert len(config.caches) == 2
    assert len(config.memory_controllers) == 2


def test_unknown_requester_fails(base_config, config_writer) -> None:
    base_config["workloads"] = [
        {
            "name": "bad",
            "type": "stream",
            "requesters": ["cpu99.t0"],
            "partid": 1,
            "pmg": 0,
            "request_size_bytes": 64,
            "injection_rate_gbps": 10,
            "read_ratio": 1.0,
            "working_set_bytes": 1_048_576,
        }
    ]
    with pytest.raises(ConfigError, match="unknown requesters"):
        load_config(config_writer(base_config))
