from __future__ import annotations

import pytest
import yaml

from src.config.loader import load_config
from src.sim.simulation import Simulation
from src.web.config_builder import (
    DEFAULT_CONTROL_INTERVAL_NS,
    DEFAULT_DURATION_NS,
    DEFAULT_L3_SETS,
    DEFAULT_L3_WAYS,
    MIN_CONTROL_INTERVAL_NS,
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
    assert config.workloads[0].address_base_bytes == 0
    assert config.workloads[1].address_base_bytes == 256 * 1024 * 1024
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
    assert config.caches[0].sets == DEFAULT_L3_SETS == 20 * 1024
    assert config.caches[0].ways == DEFAULT_L3_WAYS == 20
    assert config.caches[0].monitor_group_sets == 8
    assert config.caches[0].queue_depth == 128
    assert config.caches[0].lookup_parallelism == 16
    assert config.caches[0].miss_detect_latency_ns == 20
    assert config.caches[0].fill_latency_ns == 10
    assert config.caches[0].mshr_entries == 64
    assert config.caches[0].fill_buffer_entries == 16
    assert config.caches[0].merge_same_line_misses is False
    assert config.caches[0].replacement_policy == "lru"
    assert config.caches[0].clock_mhz == 1_000
    assert config.caches[0].monitor_period_cycles == 256
    assert config.caches[0].sampling_mode == "fixed_first"
    assert config.caches[0].sampling_rotation_period_monitor_cycles == 1
    assert config.caches[0].history_weight == 0.75
    assert config.caches[0].current_weight == 0.25
    assert config.caches[0].cbusy_response_enable is False
    assert config.caches[0].qos_scheduler_enable is False
    assert config.caches[0].cbusy_qos_demote_per_level == 1
    assert config.ostd.cbusy_response_enable is False
    assert config.controls_by_msc["slc0"][0].cpbm_enable is True
    assert config.controls_by_msc["slc0"][0].cache_portion_bitmap == "fffff"
    assert config.controls_by_msc["mc0"][0].cbusy_enable is False
    assert config.memory_controllers[0].cbusy_sample_ns == 1_000
    assert config.memory_controllers[0].clock_mhz == 1_000
    assert config.memory_controllers[0].monitor_period_cycles == 256
    assert config.memory_controllers[0].history_weight == 0.75
    assert config.memory_controllers[0].current_weight == 0.25
    assert config.memory_controllers[0].bandwidth_hysteresis == 0.05
    assert config.memory_controllers[0].aging_mode == "none"
    assert config.memory_controllers[0].token_bucket_window_ns == 100
    assert config.memory_controllers[0].bmin_qos_promote == 2
    assert config.memory_controllers[0].softlimit_qos_demote == 2
    assert config.memory_controllers[0].qos_map_8_to_4_enable is False
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


def test_web_defaults_use_short_interactive_timing(tmp_path) -> None:
    parameters = default_parameters()

    assert parameters["duration_ns"] == DEFAULT_DURATION_NS == 5_000
    assert parameters["control_interval_ns"] == DEFAULT_CONTROL_INTERVAL_NS == 128

    raw = build_config(parameters, str(tmp_path / "run"))
    assert raw["simulation"]["time_ns"] == DEFAULT_DURATION_NS
    assert raw["simulation"]["control_interval_ns"] == DEFAULT_CONTROL_INTERVAL_NS


def test_web_control_interval_minimum_is_128ns(tmp_path) -> None:
    parameters = default_parameters()
    parameters["control_interval_ns"] = MIN_CONTROL_INTERVAL_NS
    raw = build_config(parameters, str(tmp_path / "min"))
    assert raw["simulation"]["control_interval_ns"] == MIN_CONTROL_INTERVAL_NS

    parameters["control_interval_ns"] = MIN_CONTROL_INTERVAL_NS - 1
    with pytest.raises(ParameterError, match="control_interval_ns"):
        build_config(parameters, str(tmp_path / "too_small"))


def test_resctrl_disabled_keeps_direct_thread_labels(tmp_path) -> None:
    parameters = default_parameters()
    assert parameters["resctrl_enabled"] is False

    raw = build_config(parameters, str(tmp_path / "direct"))

    assert raw["software"]["resctrl"]["enabled"] is False
    assert [row["partid"] for row in raw["workloads"]] == list(range(16))
    assert [row["pmg"] for row in raw["workloads"]] == list(range(16))


def test_resctrl_groups_map_tasks_cpus_and_schema(tmp_path) -> None:
    parameters = default_parameters()
    parameters["resctrl_enabled"] = True
    parameters["l3_instances"] = 2
    parameters["memory_controllers"] = 2
    parameters["resctrl_groups"] = [
        {
            "enabled": True,
            "name": "root",
            "partid": 0,
            "mode": "shareable",
            "schemata": "L3:0=fffff\nMB:0=256",
            "tasks": "",
            "cpus": "0-15",
            "mb_limit_mode": "softlimit",
            "mon_groups": "",
        },
        {
            "enabled": True,
            "name": "latency",
            "partid": 5,
            "mode": "shareable",
            "schemata": "L3:0=003ff;1=0000f\nMB:0=80;1=40",
            "tasks": "thread_01",
            "cpus": "",
            "mb_limit_mode": "hardlimit",
            "mon_groups": "latency_mon|3|thread_01|",
        },
        {
            "enabled": True,
            "name": "background",
            "partid": 6,
            "mode": "shareable",
            "schemata": "L3:0=ffc00\nMB:0=60",
            "tasks": "",
            "cpus": "2-3",
            "mb_limit_mode": "softlimit",
            "mon_groups": "bg_mon|2||2-3",
        },
    ]

    raw = build_config(parameters, str(tmp_path / "resctrl"))
    config_path = tmp_path / "resctrl.yaml"
    config_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )
    config = load_config(config_path)
    workloads = {workload.name: workload for workload in config.workloads}

    assert workloads["thread_00"].partid == 0
    assert workloads["thread_00"].pmg == 0
    assert workloads["thread_01"].partid == 5
    assert workloads["thread_01"].pmg == 3
    assert workloads["thread_02"].partid == 6
    assert workloads["thread_02"].pmg == 2
    assert workloads["thread_03"].partid == 6
    assert workloads["thread_03"].pmg == 2

    assert config.partitions[5] == "latency"
    slc0_latency = config.controls_by_msc["slc0"][5]
    slc1_latency = config.controls_by_msc["slc1"][5]
    assert slc0_latency.cache_portion_bitmap == "003ff"
    assert slc1_latency.cache_portion_bitmap == "0000f"
    assert slc0_latency.cmin_enable is False
    assert slc0_latency.cmax_enable is False
    assert config.controls_by_msc["mc0"][5].bw_max_gbps == 80
    assert config.controls_by_msc["mc1"][5].bw_max_gbps == 40
    assert config.controls_by_msc["mc0"][5].bw_limit_mode == "hardlimit"
    assert raw["software"]["resctrl"]["enabled"] is True


def test_resctrl_rejects_duplicate_partids(tmp_path) -> None:
    parameters = default_parameters()
    parameters["resctrl_enabled"] = True
    parameters["resctrl_groups"] = [
        {
            "enabled": True,
            "name": "root",
            "partid": 0,
            "schemata": "L3:0=ffff\nMB:0=256",
            "tasks": "",
            "cpus": "0-15",
        },
        {
            "enabled": True,
            "name": "dup",
            "partid": 0,
            "schemata": "L3:0=ffff\nMB:0=256",
            "tasks": "thread_01",
            "cpus": "",
        },
    ]

    with pytest.raises(ParameterError, match="unique PARTID"):
        build_config(parameters, str(tmp_path / "bad"))


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
    parameters["control_interval_ns"] = 5_000
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
        assert parameters["duration_ns"] == DEFAULT_DURATION_NS
        assert parameters["control_interval_ns"] == DEFAULT_CONTROL_INTERVAL_NS
        assert len(parameters["stimulus_configs"]) == 16
        assert len(parameters["partid_configs"]) == 16
        assert [row["slot"] for row in parameters["stimulus_configs"]] == list(range(16))
        assert [row["partid"] for row in parameters["partid_configs"]] == list(range(16))
        assert any(row["enabled"] for row in parameters["stimulus_configs"])
        raw = build_config(parameters, str(tmp_path / preset["id"]))
        assert raw["simulation"]["time_ns"] > 0
        assert len(raw["workloads"]) >= 1


def test_mc_competition_preset_keeps_both_partids_visible(tmp_path) -> None:
    preset = next(
        preset
        for preset in control_effect_presets()
        if preset["id"] == "mc_bmin_qos_compete"
    )
    parameters = preset["parameters"]
    active_rows = {
        row["partid"]: row
        for row in parameters["stimulus_configs"]
        if row["enabled"]
    }
    assert active_rows[0]["address_base_mb"] != active_rows[1]["address_base_mb"]

    raw = build_config(parameters, str(tmp_path / "mc_bmin_qos_compete"))
    config_path = tmp_path / "mc_bmin_qos_compete.yaml"
    config_path.write_text(
        yaml.safe_dump(raw, sort_keys=False),
        encoding="utf-8",
    )
    config = load_config(config_path)
    workloads = {workload.partid: workload for workload in config.workloads}
    assert workloads[0].address_base_bytes != workloads[1].address_base_bytes
    result = Simulation.from_config(config).run()
    mc_rows = [
        row for row in result.collector.msc_rows
        if row["msc_type"] == "memory_controller"
    ]
    partid0_requests = sum(row["per_partid"]["0"]["requests"] for row in mc_rows)
    partid1_requests = sum(row["per_partid"]["1"]["requests"] for row in mc_rows)
    partid0_peak_bw = max(
        row["per_partid"]["0"]["achieved_bandwidth_gbps"]
        for row in mc_rows
    )
    partid1_peak_bw = max(
        row["per_partid"]["1"]["achieved_bandwidth_gbps"]
        for row in mc_rows
    )
    assert partid0_requests > 0
    assert partid1_requests > 0
    assert partid1_peak_bw > 1.0
    assert partid0_peak_bw >= partid1_peak_bw


def test_p1_presets_emit_minimal_closed_loop_evidence(tmp_path) -> None:
    presets = {
        preset["id"]: preset["parameters"]
        for preset in control_effect_presets()
    }

    l3_raw = build_config(
        presets["l3_cmin_cmax_pressure"],
        str(tmp_path / "l3_cmax"),
    )
    l3_path = tmp_path / "l3_cmax.yaml"
    l3_path.write_text(yaml.safe_dump(l3_raw, sort_keys=False), encoding="utf-8")
    l3_result = Simulation.from_config(load_config(l3_path)).run()
    l3_rows = [
        row for row in l3_result.collector.msc_rows
        if row["msc_type"] == "cache"
    ]
    l3_partid1 = [
        row["per_partid"]["1"] for row in l3_rows
    ]
    assert sum(row["cmax_growth_blocks"] for row in l3_partid1) > 0
    assert sum(row["self_replacements"] for row in l3_partid1) > 0
    l3_limit_events = [
        row for row in l3_result.collector.control_rows
        if row["policy"] == "l3_cmin_cmax"
        and row["event_type"] == "limit_state_changed"
    ]
    l3_sample_ids = {
        row["sample_id"]
        for row in l3_result.collector.monitor_sample_rows
        if row["semantic"] == "control_input"
    }
    assert l3_limit_events
    assert all(row["monitor_sample_id"] in l3_sample_ids for row in l3_limit_events)

    mc_raw = build_config(
        presets["mc_hard_bmax_cbusy"],
        str(tmp_path / "mc_bmax_cbusy"),
    )
    mc_path = tmp_path / "mc_bmax_cbusy.yaml"
    mc_path.write_text(yaml.safe_dump(mc_raw, sort_keys=False), encoding="utf-8")
    mc_result = Simulation.from_config(load_config(mc_path)).run()
    mc_rows = [
        row for row in mc_result.collector.msc_rows
        if row["msc_type"] == "memory_controller"
    ]
    assert sum(
        row["per_partid"]["0"]["hardlimit_block_events"]
        for row in mc_rows
    ) > 0
    mc_limit_events = [
        row for row in mc_result.collector.control_rows
        if row["policy"] == "mc_bmin_bmax"
        and row["event_type"] == "limit_state_changed"
    ]
    mc_sample_ids = {
        row["sample_id"]
        for row in mc_result.collector.monitor_sample_rows
        if row["semantic"] == "control_input"
    }
    assert mc_limit_events
    assert all(row["monitor_sample_id"] in mc_sample_ids for row in mc_limit_events)
    assert any(row["outcome_state"] == "overshoot" for row in mc_limit_events)
    cpu_rows = [
        row for row in mc_result.collector.requester_rows
        if row["partid"] == 0
    ]
    assert cpu_rows[-1]["effective_max_outstanding"] < 32
    cbusy_events = [
        row for row in mc_result.collector.control_rows
        if row["policy"] == "mc_cbusy"
    ]
    assert cbusy_events
    assert all(row["monitor_sample_id"] for row in cbusy_events)
    assert all(row["decision_id"] for row in cbusy_events)
    assert all(
        row["action_effective_time_ns"] >= row["details"]["sample_time_ns"]
        for row in cbusy_events
    )


def test_defaults_payload_contains_control_effect_presets() -> None:
    payload = defaults_payload()
    assert "parameters" in payload
    assert "ui_metadata" in payload
    assert payload["parameters"]["duration_ns"] == DEFAULT_DURATION_NS
    assert payload["parameters"]["control_interval_ns"] == DEFAULT_CONTROL_INTERVAL_NS
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
