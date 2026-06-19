from __future__ import annotations

import pytest
import yaml

from src.config.loader import load_config
from src.web.config_builder import ParameterError, build_config, default_parameters


def test_web_parameters_build_valid_multicore_config(tmp_path) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "l3_instances": 3,
            "memory_controllers": 3,
            "duration_ns": 100_000,
            "control_interval_ns": 20_000,
        }
    )
    raw = build_config(parameters, str(tmp_path / "run"))
    config_path = tmp_path / "web.yaml"
    config_path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    config = load_config(config_path)
    assert len(config.requesters) == 16
    assert len(config.caches) == 3
    assert len(config.memory_controllers) == 3
    assert len(config.workloads) == 16
    assert {
        workload.requesters[0]
        for workload in config.workloads
    } == {
        f"cpu{core}.t{thread}"
        for core in range(8)
        for thread in range(2)
    }
    assert [workload.partid for workload in config.workloads] == list(range(16))
    assert config.workloads[0].injection_rate_gbps == 6.0
    assert config.workloads[1].injection_rate_mrps == 4.0
    assert config.policies[0].params["protected_partids"] == [1]
    assert config.policies[0].params["background_partids"] == [
        0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
    ]
    assert len(config.partitions) == 16
    assert len(config.controls_by_msc["slc0"]) == 16
    assert len(config.controls_by_msc["mc0"]) == 16
    assert config.caches[0].sets == 32_768
    assert config.caches[0].monitor_group_sets == 8


def test_web_parameters_reject_mask_larger_than_cache(tmp_path) -> None:
    parameters = default_parameters()
    parameters["l3_ways"] = 4
    parameters["partid_configs"][1]["cpbm"] = "ff"
    with pytest.raises(ParameterError, match="exceeds configured"):
        build_config(parameters, str(tmp_path / "run"))


def test_web_parameters_reject_excessive_request_count(tmp_path) -> None:
    parameters = default_parameters()
    parameters["duration_ns"] = 5_000_000
    for row in parameters["stimulus_configs"]:
        row.update(
            {
                "rate_value": 4096,
                "rate_unit": "gbps",
            }
        )
    with pytest.raises(ParameterError, match="Estimated request count"):
        build_config(parameters, str(tmp_path / "run"))


def test_web_parameters_can_disable_one_thread(tmp_path) -> None:
    parameters = default_parameters()
    parameters["stimulus_configs"][7]["enabled"] = False
    raw = build_config(parameters, str(tmp_path / "run"))
    requester_sets = [row["requesters"] for row in raw["workloads"]]
    assert len(requester_sets) == 15
    assert ["cpu3.t1"] not in requester_sets
