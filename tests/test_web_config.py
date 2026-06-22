from __future__ import annotations

import pytest
import yaml

from src.config.loader import load_config
from src.sim.simulation import Simulation
from src.web.config_builder import (
    ParameterError,
    build_config,
    control_effect_presets,
    default_parameters,
)
from src.web.server import (
    ControlVerificationManager,
    Job,
    defaults_payload,
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
    assert config.workloads[1].address_pattern == "pointer_chase"
    assert config.workloads[1].dependency_mode == "pointer_chain"
    assert config.workloads[3].address_pattern == "uniform_random"
    assert config.workloads[0].issue_selection == "eligible_scan"
    assert config.workloads[0].source_queue_depth == 4
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
    assert config.caches[0].miss_detect_latency_ns == 20
    assert config.caches[0].fill_latency_ns == 10
    assert config.caches[0].mshr_entries == 64
    assert config.caches[0].fill_buffer_entries == 16
    assert config.caches[0].merge_same_line_misses is True
    assert config.caches[0].replacement_policy == "lru"
    assert config.caches[0].clock_mhz == 1_000
    assert config.caches[0].monitor_period_cycles == 256
    assert config.caches[0].history_weight == 192
    assert config.caches[0].current_weight == 64
    assert config.controls_by_msc["slc0"][0].cpbm_enable is True
    assert config.controls_by_msc["mc0"][0].cbusy_enable is False
    assert config.memory_controllers[0].cbusy_sample_ns == 1_000
    assert config.memory_controllers[0].clock_mhz == 1_000
    assert config.memory_controllers[0].monitor_period_cycles == 256
    assert config.memory_controllers[0].history_weight == 192
    assert config.memory_controllers[0].current_weight == 64
    assert config.memory_controllers[0].bandwidth_hysteresis == 0.05
    assert config.memory_controllers[0].aging_mode == "none"
    assert config.memory_controllers[0].token_bucket_window_ns == 100
    assert config.memory_controllers[0].bmin_qos_promote == 2
    assert config.memory_controllers[0].softlimit_qos_demote == 2
    assert config.address_interleave.mode == "linear"
    assert config.address_interleave.granularity_bytes == 256
    assert config.address_interleave.xor_shift == 12
    assert config.noc.topology == (
        "three_bidirectional_bufferless_rings"
    )
    assert config.noc.clock_mhz == 1000
    assert config.noc.flit_bytes == 16
    assert config.noc.link_slots_per_direction == 1
    assert config.noc.hop_latency_cycles == 1
    assert config.noc.tie_direction == "cw"
    assert set(config.noc.ring_node_order) >= {
        "r0",
        "slc0",
        "mc0",
    }
    assert config.ostd.core_max_outstanding == 48
    assert config.ostd.core_policy == "shared"
    assert config.ostd.thread_reserve == 8


def test_memory_interleave_is_deterministic_and_configurable(
    tmp_path,
) -> None:
    parameters = default_parameters()
    parameters["memory_controllers"] = 3
    raw = build_config(parameters, str(tmp_path / "linear"))
    path = tmp_path / "linear.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    linear = Simulation.from_config(load_config(path))
    assert [
        linear._destination_mc_for("cpu0.t0", address)
        for address in (0, 256, 512, 768)
    ] == ["mc0", "mc1", "mc2", "mc0"]

    parameters["mc_interleave_mode"] = "xor"
    parameters["mc_interleave_xor_shift"] = 9
    raw = build_config(parameters, str(tmp_path / "xor"))
    path = tmp_path / "xor.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    first = Simulation.from_config(load_config(path))
    second = Simulation.from_config(load_config(path))
    addresses = (0, 256, 512, 4096, 8192)
    assert [
        first._destination_mc_for("cpu0.t0", address)
        for address in addresses
    ] == [
        second._destination_mc_for("cpu0.t0", address)
        for address in addresses
    ]


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


def test_web_parameters_reject_impossible_thread_reserves(
    tmp_path,
) -> None:
    parameters = default_parameters()
    parameters.update(
        {
            "core_ostd_policy": "reserve_borrow",
            "core_max_outstanding": 12,
            "thread_ostd_reserve": 8,
        }
    )
    with pytest.raises(ParameterError, match="reserve_borrow"):
        build_config(parameters, str(tmp_path / "run"))


def test_web_parameters_reject_invalid_ring_direction(
    tmp_path,
) -> None:
    parameters = default_parameters()
    parameters["noc_tie_direction"] = "load_balanced"
    with pytest.raises(ParameterError, match="noc_tie_direction"):
        build_config(parameters, str(tmp_path / "run"))


def test_web_parameters_reject_plru_with_non_power_of_two_ways(
    tmp_path,
) -> None:
    parameters = default_parameters()
    parameters["l3_ways"] = 3
    parameters["l3_replacement_policy"] = "plru"
    for row in parameters["partid_configs"]:
        row["cpbm"] = "7"
        row["cmin"] = 0
        row["cmax"] = 100
    with pytest.raises(ParameterError, match="PLRU"):
        build_config(parameters, str(tmp_path / "run"))


def test_control_effect_presets_are_buildable(tmp_path) -> None:
    presets = control_effect_presets()
    assert len(presets) >= 4
    assert {
        "mc_hard_bmax_cbusy",
        "mc_bmin_qos_compete",
        "l3_cmin_cmax_pressure",
        "mixed_control_overview",
    } <= {preset["id"] for preset in presets}
    for preset in presets:
        parameters = preset["parameters"]
        assert len(parameters["stimulus_configs"]) == 16
        assert len(parameters["partid_configs"]) == 16
        assert [row["slot"] for row in parameters["stimulus_configs"]] == list(range(16))
        assert [row["partid"] for row in parameters["partid_configs"]] == list(range(16))
        assert any(row["enabled"] for row in parameters["stimulus_configs"])
        raw = build_config(parameters, str(tmp_path / preset["id"]))
        assert raw["simulation"]["time_ns"] > 0
        assert len(raw["workloads"]) >= 1


def test_defaults_payload_contains_control_effect_presets() -> None:
    payload = defaults_payload()
    assert "parameters" in payload
    assert "ui_metadata" in payload
    assert len(payload["presets"]) >= 4
    for preset in payload["presets"]:
        assert set(preset) == {
            "id",
            "name",
            "summary",
            "expected",
            "parameters",
        }


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
            "mc_qos_enable",
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

    assert len(cases) == 13
    assert cases["cmin_on"]["partid_configs"][0]["cmin_enable"] is True
    assert cases["cmax_limited"]["partid_configs"][0]["cmax"] == 12.5
    assert cases["qos_split"]["partid_configs"][0]["mc_qos"] == 7
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
    assert job.result["passed"] == job.result["total"] == 7
    assert {row["id"] for row in job.result["checks"]} == {
        "cmin",
        "cmax",
        "mc_qos",
        "bmin",
        "bmax_soft_uncontended",
        "bmax_hard",
        "bmax_soft_contended",
    }
