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


def test_l3_cmin_total_cannot_exceed_physical_capacity(
    base_config,
    config_writer,
) -> None:
    base_config["mpam"]["msc_controls"] = [
        {
            "msc_id": "slc0",
            "controls": [
                {"partid": 1, "cmin_percent": 60, "cmax_percent": 100},
                {"partid": 2, "cmin_percent": 50, "cmax_percent": 100},
            ],
        }
    ]
    with pytest.raises(ConfigError, match="CMIN total exceeds 100"):
        load_config(config_writer(base_config))


def test_l3_cmin_must_fit_cpbm_reachable_capacity(
    base_config,
    config_writer,
) -> None:
    base_config["mpam"]["msc_controls"] = [
        {
            "msc_id": "slc0",
            "controls": [
                {
                    "partid": 1,
                    "cpbm": "1",
                    "cmin_percent": 50,
                    "cmax_percent": 100,
                },
            ],
        }
    ]
    with pytest.raises(ConfigError, match="CPBM reachable"):
        load_config(config_writer(base_config))


def test_mc_qos_is_three_bit(base_config, config_writer) -> None:
    base_config["mpam"]["msc_controls"] = [
        {
            "msc_id": "mc0",
            "controls": [{"partid": 1, "mc_qos": 8}],
        }
    ]
    with pytest.raises(ConfigError, match="mc_qos"):
        load_config(config_writer(base_config))
