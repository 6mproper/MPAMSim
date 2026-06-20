from __future__ import annotations

import pytest
import yaml

from src.config.loader import load_config
from src.sim.simulation import Simulation
from src.web.config_builder import ParameterError, build_config, default_parameters
from src.web.server import (
    ControlVerificationManager,
    Job,
    derive_control_verification_cases,
    derive_experiment_cases,
    summarize_experiment_result,
)


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
    assert config.caches[0].queue_depth == 128
    assert config.caches[0].lookup_parallelism == 16
    assert config.controls_by_msc["slc0"][0].cpbm_enable is True
    assert config.controls_by_msc["mc0"][0].cbusy_enable is False
    assert config.memory_controllers[0].cbusy_sample_ns == 1_000
    assert config.memory_controllers[0].token_bucket_window_ns == 100
    assert config.memory_controllers[0].bmin_priority_boost == 16
    assert config.memory_controllers[0].softlimit_priority_penalty == 16


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


def test_web_parameters_reject_unordered_cbusy_thresholds(tmp_path) -> None:
    parameters = default_parameters()
    parameters["cbusy_l1_queue_ratio"] = 0.8
    parameters["cbusy_l2_queue_ratio"] = 0.4
    with pytest.raises(ParameterError, match="queue ratios"):
        build_config(parameters, str(tmp_path / "run"))


def test_experiment_cases_only_change_bmax_and_cbusy_enables() -> None:
    parameters = default_parameters()
    cases = derive_experiment_cases(parameters)

    assert list(cases) == [
        "reference",
        "bmax_only",
        "cbusy_only",
        "combined",
    ]
    assert all(case["seed"] == parameters["seed"] for case in cases.values())
    assert all(case["policy"] == "static_mpam" for case in cases.values())

    reference = cases["reference"]["partid_configs"][0]
    bmax = cases["bmax_only"]["partid_configs"][0]
    cbusy = cases["cbusy_only"]["partid_configs"][0]
    combined = cases["combined"]["partid_configs"][0]
    assert reference["bmax_enable"] is False
    assert reference["cbusy_enable"] is False
    assert bmax["bmax_enable"] is True
    assert bmax["cbusy_enable"] is False
    assert cbusy["bmax_enable"] is False
    assert cbusy["cbusy_enable"] is True
    assert combined["bmax_enable"] is True
    assert combined["cbusy_enable"] is True
    assert all(
        not combined[field]
        for field in (
            "cpbm_enable",
            "cmin_enable",
            "cmax_enable",
            "bmin_enable",
            "priority_enable",
        )
    )


def test_experiment_summary_contains_system_and_partid_evidence(tmp_path) -> None:
    parameters = default_parameters()
    parameters["duration_ns"] = 20_000
    parameters["control_interval_ns"] = 5_000
    for row in parameters["stimulus_configs"][2:]:
        row["enabled"] = False
    raw = build_config(parameters, str(tmp_path / "experiment"))
    config_path = tmp_path / "experiment.yaml"
    config_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )

    summary = summarize_experiment_result(
        Simulation.from_config(load_config(config_path)).run()
    )

    assert summary["simulation_time_ns"] == 20_000
    assert summary["total_throughput_gbps"] >= 0
    assert summary["mc_queue_peak"] >= 0
    assert summary["mc_queue_area_entry_ns"] >= 0
    assert set(summary["per_partid"]) >= {"0", "1"}
    assert "effective_ostd_min" in summary["per_partid"]["0"]


def test_control_verification_cases_isolate_mechanisms() -> None:
    cases = derive_control_verification_cases(default_parameters())

    assert len(cases) == 11
    assert cases["cmin_on"]["partid_configs"][0]["cmin_enable"] is True
    assert cases["cmax_limited"]["partid_configs"][0]["cmax"] == 2
    assert cases["bmin_on"]["partid_configs"][0]["bmin_enable"] is True
    assert cases["bmax_solo_soft"]["partid_configs"][0]["limit_mode"] == "softlimit"
    assert cases["bmax_solo_hard"]["partid_configs"][0]["limit_mode"] == "hardlimit"
    assert cases["bmax_contended_soft"]["stimulus_configs"][1]["enabled"] is True


def test_control_verification_suite_passes_default_algorithms(
    tmp_path,
    monkeypatch,
) -> None:
    import src.web.server as web_server

    monkeypatch.setattr(web_server, "RUN_ROOT", tmp_path)
    job = Job(id="verification", parameters=default_parameters())

    ControlVerificationManager()._run(job)

    assert job.status == "completed"
    assert job.result["passed"] == job.result["total"] == 6
    assert {row["id"] for row in job.result["checks"]} == {
        "cmin",
        "cmax",
        "bmin",
        "bmax_soft_uncontended",
        "bmax_hard",
        "bmax_soft_contended",
    }
