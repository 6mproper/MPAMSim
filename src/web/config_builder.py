from __future__ import annotations

import math
from typing import Dict, List


class ParameterError(ValueError):
    pass


def _number(
    values: Dict[str, object],
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(values.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ParameterError(f"{name} must be numeric") from exc
    if not minimum <= value <= maximum:
        raise ParameterError(
            f"{name} must be in [{minimum}, {maximum}]"
        )
    return value


def _integer(
    values: Dict[str, object],
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    return int(
        _number(values, name, default, minimum, maximum)
    )


def _choice(
    values: Dict[str, object],
    name: str,
    default: str,
    choices: List[str],
) -> str:
    value = str(values.get(name, default))
    if value not in choices:
        raise ParameterError(
            f"{name} must be one of {choices}"
        )
    return value


def _mask(value: object, ways: int, default: int) -> str:
    text = (
        str(value or "")
        .strip()
        .lower()
        .removeprefix("0x")
    )
    try:
        parsed = int(text, 16) if text else default
    except ValueError as exc:
        raise ParameterError(
            f"Invalid CPBM: {value}"
        ) from exc
    maximum = (1 << ways) - 1
    if parsed < 0 or parsed > maximum:
        raise ParameterError(
            f"CPBM 0x{parsed:x} exceeds configured {ways} ways"
        )
    width = max(1, math.ceil(ways / 4))
    return f"{parsed:0{width}x}"


def _default_partid_configs(
    ways: int = 16,
    total_mc_bandwidth: float = 256.0,
    max_outstanding: int = 32,
) -> List[Dict[str, object]]:
    full_mask = (1 << ways) - 1
    lower_ways = max(1, ways // 2)
    lower_mask = (1 << lower_ways) - 1
    upper_mask = full_mask ^ lower_mask
    width = max(1, math.ceil(ways / 4))
    rows = []
    for partid in range(16):
        row = {
            "partid": partid,
            "name": f"partid_{partid}",
            "monitor_enable": True,
            "cpbm_enable": True,
            "cmin_enable": True,
            "cmax_enable": True,
            "cmin": 0,
            "cmax": ways,
            "cpbm": f"{full_mask:0{width}x}",
            "bmin_enable": True,
            "bmax_enable": True,
            "bmin_gbps": 0.0,
            "bmax_gbps": total_mc_bandwidth,
            "limit_mode": "softlimit",
            "priority_enable": True,
            "priority": 4,
            "cbusy_enable": False,
            "cbusy_l1_ostd": max(1, min(max_outstanding, math.ceil(max_outstanding * 0.75))),
            "cbusy_l2_ostd": max(1, min(max_outstanding, math.ceil(max_outstanding * 0.50))),
            "cbusy_l3_ostd": max(1, min(max_outstanding, math.ceil(max_outstanding * 0.125))),
        }
        rows.append(row)
    rows[0].update({"name": "default", "priority": 4})
    rows[1].update(
        {
            "name": "latency_sensitive",
            "cmin": max(1, lower_ways // 2),
            "cmax": lower_ways,
            "cpbm": f"{lower_mask:0{width}x}",
            "bmin_gbps": min(40.0, total_mc_bandwidth),
            "bmax_gbps": min(120.0, total_mc_bandwidth),
            "limit_mode": "hardlimit",
            "priority": 12,
        }
    )
    rows[2].update(
        {
            "name": "background_bandwidth",
            "cmin": 0,
            "cmax": ways - lower_ways,
            "cpbm": f"{upper_mask:0{width}x}",
            "bmin_gbps": 0.0,
            "bmax_gbps": min(80.0, total_mc_bandwidth),
            "limit_mode": "hardlimit",
            "priority": 4,
        }
    )
    return rows


def _thread_requester(slot: int) -> str:
    return f"cpu{slot // 2}.t{slot % 2}"


def _default_stimulus_configs() -> List[Dict[str, object]]:
    rows = []
    workload_types = [
        "mixed_rw",
        "pointer_chase",
        "stream",
        "random_read",
    ]
    for slot in range(16):
        workload_type = workload_types[slot % len(workload_types)]
        row = {
            "slot": slot,
            "enabled": True,
            "requester": _thread_requester(slot),
            "partid": slot,
            "pmg": slot,
            "workload_type": workload_type,
            "rate_value": 6.0,
            "rate_unit": "gbps",
            "request_size_bytes": 64,
            "read_ratio": (
                0.75 if workload_type == "mixed_rw" else 1.0
            ),
            "working_set_mb": (
                64 if workload_type == "pointer_chase" else 256
            ),
            "target_p99_ns": 0.0,
        }
        rows.append(row)
    rows[1].update(
        {
            "rate_value": 4.0,
            "rate_unit": "mrps",
            "working_set_mb": 64,
            "target_p99_ns": 500.0,
        }
    )
    rows[2].update(
        {
            "rate_value": 12.0,
            "rate_unit": "gbps",
            "working_set_mb": 1024,
            "read_ratio": 0.8,
        }
    )
    return rows


def default_parameters() -> Dict[str, object]:
    return {
        "duration_ns": 500_000,
        "control_interval_ns": 50_000,
        "seed": 1234,
        "active_cores": 8,
        "threads_per_core": 2,
        "l3_instances": 2,
        "l3_sets": 32_768,
        "l3_ways": 16,
        "l3_line_size": 64,
        "l3_monitor_group_sets": 8,
        "l3_hit_latency_ns": 20,
        "noc_routers": 8,
        "noc_link_gbps": 256,
        "noc_router_latency_ns": 5,
        "noc_queue_depth": 64,
        "noc_virtual_channels": 4,
        "memory_controllers": 2,
        "channels_per_mc": 2,
        "channel_bandwidth_gbps": 128,
        "mc_base_latency_ns": 80,
        "mc_queue_depth": 512,
        "max_outstanding": 32,
        "cbusy_sample_ns": 1_000,
        "cbusy_feedback_latency_ns": 50,
        "cbusy_release_hold_samples": 3,
        "cbusy_l1_bw_ratio": 1.0,
        "cbusy_l2_bw_ratio": 1.1,
        "cbusy_l3_bw_ratio": 1.25,
        "cbusy_l1_queue_ratio": 0.25,
        "cbusy_l2_queue_ratio": 0.50,
        "cbusy_l3_queue_ratio": 0.75,
        "policy": "closed_loop_qos",
        "max_bw_step_percent": 10,
        "p99_hysteresis": 0.1,
        "min_hold_intervals": 3,
        "partid_configs": _default_partid_configs(),
        "stimulus_configs": _default_stimulus_configs(),
    }


def _parse_partid_configs(
    parameters: Dict[str, object],
    ways: int,
    total_mc_bandwidth: float,
    max_outstanding: int,
) -> List[Dict[str, object]]:
    raw_rows = parameters.get("partid_configs")
    if not isinstance(raw_rows, list) or len(raw_rows) != 16:
        raw_rows = _default_partid_configs(
            ways, total_mc_bandwidth, max_outstanding
        )
    full_mask = (1 << ways) - 1
    parsed = []
    seen = set()
    for index, raw in enumerate(raw_rows):
        if not isinstance(raw, dict):
            raise ParameterError(
                "Each PARTID configuration must be an object"
            )
        partid = int(raw.get("partid", index))
        if partid < 0 or partid > 15 or partid in seen:
            raise ParameterError(
                "PARTID entries must uniquely cover 0..15"
            )
        seen.add(partid)
        cpbm = _mask(
            raw.get("cpbm"),
            ways,
            full_mask,
        )
        enabled_ways = bin(int(cpbm, 16)).count("1")
        cmin = int(raw.get("cmin", 0))
        cmax = int(raw.get("cmax", enabled_ways))
        if not 0 <= cmin <= cmax <= enabled_ways:
            raise ParameterError(
                f"PARTID {partid}: require 0 <= CMIN <= CMAX <= CPBM ways"
            )
        try:
            bmin = float(raw.get("bmin_gbps", 0.0))
            bmax = float(
                raw.get(
                    "bmax_gbps",
                    total_mc_bandwidth,
                )
            )
        except (TypeError, ValueError) as exc:
            raise ParameterError(
                f"PARTID {partid}: BMIN/BMAX must be numeric"
            ) from exc
        if not 0 <= bmin <= bmax <= 4096:
            raise ParameterError(
                f"PARTID {partid}: require 0 <= BMIN <= BMAX <= 4096"
            )
        limit_mode = str(
            raw.get("limit_mode", "softlimit")
        )
        if limit_mode not in {
            "softlimit",
            "hardlimit",
        }:
            raise ParameterError(
                f"PARTID {partid}: invalid limit mode"
            )
        priority = int(raw.get("priority", 4))
        if not 0 <= priority <= 15:
            raise ParameterError(
                f"PARTID {partid}: priority must be 0..15"
            )
        cbusy_l1_ostd = min(
            max_outstanding,
            int(
            raw.get(
                "cbusy_l1_ostd",
                max(1, math.ceil(max_outstanding * 0.75)),
            )
            ),
        )
        cbusy_l2_ostd = min(
            cbusy_l1_ostd,
            int(
            raw.get(
                "cbusy_l2_ostd",
                max(1, math.ceil(max_outstanding * 0.50)),
            )
            ),
        )
        cbusy_l3_ostd = min(
            cbusy_l2_ostd,
            int(
            raw.get(
                "cbusy_l3_ostd",
                max(1, math.ceil(max_outstanding * 0.125)),
            )
            ),
        )
        if not (
            1
            <= cbusy_l3_ostd
            <= cbusy_l2_ostd
            <= cbusy_l1_ostd
            <= max_outstanding
        ):
            raise ParameterError(
                f"PARTID {partid}: require 1 <= CBusy L3 <= L2 <= L1 <= max outstanding"
            )
        parsed.append(
            {
                "partid": partid,
                "name": str(
                    raw.get("name", f"partid_{partid}")
                )[:32],
                "monitor_enable": bool(
                    raw.get("monitor_enable", True)
                ),
                "cpbm_enable": bool(raw.get("cpbm_enable", True)),
                "cmin_enable": bool(raw.get("cmin_enable", True)),
                "cmax_enable": bool(raw.get("cmax_enable", True)),
                "cmin": cmin,
                "cmax": cmax,
                "cpbm": cpbm,
                "bmin_enable": bool(raw.get("bmin_enable", True)),
                "bmax_enable": bool(raw.get("bmax_enable", True)),
                "bmin_gbps": bmin,
                "bmax_gbps": bmax,
                "limit_mode": limit_mode,
                "priority_enable": bool(raw.get("priority_enable", True)),
                "priority": priority,
                "cbusy_enable": bool(raw.get("cbusy_enable", False)),
                "cbusy_l1_ostd": cbusy_l1_ostd,
                "cbusy_l2_ostd": cbusy_l2_ostd,
                "cbusy_l3_ostd": cbusy_l3_ostd,
            }
        )
    if seen != set(range(16)):
        raise ParameterError(
            "PARTID entries must cover every value 0..15"
        )
    return sorted(parsed, key=lambda row: row["partid"])


def _parse_stimulus_configs(
    parameters: Dict[str, object],
) -> List[Dict[str, object]]:
    raw_rows = parameters.get("stimulus_configs")
    if not isinstance(raw_rows, list) or len(raw_rows) != 16:
        raise ParameterError(
            "stimulus_configs must contain exactly 16 thread rows"
        )
    parsed = []
    seen = set()
    workload_types = {
        "stream",
        "pointer_chase",
        "random_read",
        "mixed_rw",
        "bursty_dma",
    }
    for index, raw in enumerate(raw_rows):
        if not isinstance(raw, dict):
            raise ParameterError(
                "Each stimulus configuration must be an object"
            )
        slot = int(raw.get("slot", index))
        if slot < 0 or slot > 15 or slot in seen:
            raise ParameterError(
                "Stimulus slots must uniquely cover 0..15"
            )
        seen.add(slot)
        enabled = bool(raw.get("enabled", True))
        partid = int(raw.get("partid", slot))
        pmg = int(raw.get("pmg", slot))
        if not 0 <= partid <= 15:
            raise ParameterError(
                f"Stimulus {slot}: PARTID must be 0..15"
            )
        if not 0 <= pmg <= 15:
            raise ParameterError(
                f"Stimulus {slot}: PMG must be 0..15"
            )
        workload_type = str(
            raw.get("workload_type", "stream")
        )
        if workload_type not in workload_types:
            raise ParameterError(
                f"Stimulus {slot}: unsupported workload type"
            )
        rate_unit = str(raw.get("rate_unit", "gbps")).lower()
        if rate_unit not in {"mrps", "gbps"}:
            raise ParameterError(
                f"Stimulus {slot}: rate unit must be mrps or gbps"
            )
        try:
            rate_value = float(raw.get("rate_value", 0.0))
            request_size = int(raw.get("request_size_bytes", 64))
            read_ratio = float(raw.get("read_ratio", 1.0))
            working_set_mb = int(raw.get("working_set_mb", 64))
            target_p99 = float(raw.get("target_p99_ns", 0.0) or 0.0)
        except (TypeError, ValueError) as exc:
            raise ParameterError(
                f"Stimulus {slot}: numeric field is invalid"
            ) from exc
        rate_max = 1000.0 if rate_unit == "mrps" else 4096.0
        if rate_value < 0 or rate_value > rate_max:
            raise ParameterError(
                f"Stimulus {slot}: rate exceeds {rate_max:g} {rate_unit}"
            )
        if enabled and rate_value <= 0:
            raise ParameterError(
                f"Stimulus {slot}: enabled rate must be positive"
            )
        if not 16 <= request_size <= 4096:
            raise ParameterError(
                f"Stimulus {slot}: request size must be 16..4096 bytes"
            )
        if not 0.0 <= read_ratio <= 1.0:
            raise ParameterError(
                f"Stimulus {slot}: read ratio must be in [0, 1]"
            )
        if not 1 <= working_set_mb <= 262_144:
            raise ParameterError(
                f"Stimulus {slot}: working set must be 1..262144 MB"
            )
        if not 0.0 <= target_p99 <= 1_000_000:
            raise ParameterError(
                f"Stimulus {slot}: target P99 must be 0..1000000 ns"
            )
        parsed.append(
            {
                "slot": slot,
                "enabled": enabled,
                "requester": _thread_requester(slot),
                "partid": partid,
                "pmg": pmg,
                "workload_type": workload_type,
                "rate_value": rate_value,
                "rate_unit": rate_unit,
                "request_size_bytes": request_size,
                "read_ratio": read_ratio,
                "working_set_mb": working_set_mb,
                "target_p99_ns": target_p99,
            }
        )
    if seen != set(range(16)):
        raise ParameterError(
            "Stimulus slots must cover every value 0..15"
        )
    enabled_rows = [row for row in parsed if row["enabled"]]
    if not enabled_rows:
        raise ParameterError(
            "At least one thread stimulus must be enabled"
        )
    return sorted(parsed, key=lambda row: row["slot"])


def _build_workloads(
    stimulus_configs: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    workloads = []
    for row in stimulus_configs:
        if not row["enabled"]:
            continue
        workload = {
            "name": f"thread_{row['slot']:02d}",
            "type": row["workload_type"],
            "requesters": [row["requester"]],
            "partid": row["partid"],
            "pmg": row["pmg"],
            "request_size_bytes": row["request_size_bytes"],
            "injection_scope": "per_requester",
            "read_ratio": row["read_ratio"],
            "working_set_bytes": (
                row["working_set_mb"] * 1024 * 1024
            ),
        }
        rate_field = (
            "injection_rate_mrps"
            if row["rate_unit"] == "mrps"
            else "injection_rate_gbps"
        )
        workload[rate_field] = row["rate_value"]
        if row["target_p99_ns"] > 0:
            workload["target_p99_ns"] = row["target_p99_ns"]
        workloads.append(workload)
    return workloads


def build_config(
    parameters: Dict[str, object],
    output_dir: str,
) -> Dict[str, object]:
    defaults = default_parameters()
    values = {**defaults, **parameters}

    duration_ns = _integer(
        values, "duration_ns", 500_000, 10_000, 5_000_000
    )
    control_interval_ns = _integer(
        values,
        "control_interval_ns",
        50_000,
        1_000,
        duration_ns,
    )
    seed = _integer(
        values, "seed", 1234, 0, 2_147_483_647
    )
    active_cores = _integer(
        values, "active_cores", 8, 8, 8
    )
    threads_per_core = _integer(
        values, "threads_per_core", 2, 2, 2
    )
    l3_instances = _integer(
        values,
        "l3_instances",
        2,
        1,
        min(active_cores, 8),
    )
    l3_sets = _integer(
        values, "l3_sets", 32_768, 8, 262_144
    )
    l3_ways = _integer(
        values, "l3_ways", 16, 1, 32
    )
    l3_line_size = _integer(
        values, "l3_line_size", 64, 16, 256
    )
    monitor_group_sets = _integer(
        values, "l3_monitor_group_sets", 8, 8, 8
    )
    l3_hit_latency_ns = _number(
        values, "l3_hit_latency_ns", 20, 1, 500
    )
    noc_routers = _integer(
        values, "noc_routers", 8, 1, 64
    )
    noc_link_gbps = _number(
        values, "noc_link_gbps", 256, 1, 4096
    )
    noc_router_latency_ns = _number(
        values,
        "noc_router_latency_ns",
        5,
        0.1,
        500,
    )
    noc_queue_depth = _integer(
        values, "noc_queue_depth", 64, 1, 4096
    )
    noc_virtual_channels = _integer(
        values, "noc_virtual_channels", 4, 1, 16
    )
    mc_count = _integer(
        values, "memory_controllers", 2, 1, 8
    )
    channels_per_mc = _integer(
        values, "channels_per_mc", 2, 1, 16
    )
    channel_bandwidth_gbps = _number(
        values,
        "channel_bandwidth_gbps",
        128,
        1,
        2048,
    )
    mc_base_latency_ns = _number(
        values, "mc_base_latency_ns", 80, 1, 2000
    )
    mc_queue_depth = _integer(
        values, "mc_queue_depth", 512, 1, 8192
    )
    max_outstanding = _integer(
        values, "max_outstanding", 32, 1, 1024
    )
    cbusy_sample_ns = _number(
        values, "cbusy_sample_ns", 1_000, 1, 1_000_000
    )
    cbusy_feedback_latency_ns = _number(
        values,
        "cbusy_feedback_latency_ns",
        50,
        0,
        100_000,
    )
    cbusy_release_hold_samples = _integer(
        values,
        "cbusy_release_hold_samples",
        3,
        1,
        1_000,
    )
    cbusy_bw_ratios = [
        _number(values, "cbusy_l1_bw_ratio", 1.0, 0.01, 10),
        _number(values, "cbusy_l2_bw_ratio", 1.1, 0.01, 10),
        _number(values, "cbusy_l3_bw_ratio", 1.25, 0.01, 10),
    ]
    cbusy_queue_ratios = [
        _number(values, "cbusy_l1_queue_ratio", 0.25, 0, 1),
        _number(values, "cbusy_l2_queue_ratio", 0.50, 0, 1),
        _number(values, "cbusy_l3_queue_ratio", 0.75, 0, 1),
    ]
    if cbusy_bw_ratios != sorted(cbusy_bw_ratios):
        raise ParameterError(
            "CBusy bandwidth ratios must satisfy L1 <= L2 <= L3"
        )
    if cbusy_queue_ratios != sorted(cbusy_queue_ratios):
        raise ParameterError(
            "CBusy queue ratios must satisfy L1 <= L2 <= L3"
        )
    total_mc_bandwidth = (
        channels_per_mc * channel_bandwidth_gbps
    )
    partid_configs = _parse_partid_configs(
        parameters,
        l3_ways,
        total_mc_bandwidth,
        max_outstanding,
    )
    stimulus_configs = _parse_stimulus_configs(parameters)
    workloads = _build_workloads(stimulus_configs)

    interval_count = math.ceil(
        duration_ns / control_interval_ns
    )
    if interval_count > 1000:
        raise ParameterError(
            "duration_ns / control_interval_ns must not exceed 1000 intervals"
        )
    estimated_requests = 0.0
    for row in stimulus_configs:
        if not row["enabled"]:
            continue
        if row["rate_unit"] == "mrps":
            estimated_requests += (
                duration_ns * row["rate_value"] / 1000.0
            )
        else:
            estimated_requests += (
                duration_ns
                * row["rate_value"]
                / (row["request_size_bytes"] * 8.0)
            )
    if estimated_requests > 2_000_000:
        raise ParameterError(
            "Estimated request count exceeds 2,000,000; reduce duration or thread rates"
        )

    policy = _choice(
        values,
        "policy",
        "closed_loop_qos",
        [
            "no_control",
            "static_mpam",
            "closed_loop_qos",
        ],
    )
    max_bw_step = _number(
        values, "max_bw_step_percent", 10, 1, 100
    )
    hysteresis = _number(
        values, "p99_hysteresis", 0.1, 0, 1
    )
    min_hold = _integer(
        values, "min_hold_intervals", 3, 1, 100
    )

    cores = [f"cpu{index}" for index in range(active_cores)]
    clusters = []
    cache_core_map: Dict[str, List[str]] = {
        f"slc{index}": []
        for index in range(l3_instances)
    }
    for cluster_index, start in enumerate(
        range(0, active_cores, 4)
    ):
        cluster_cores = cores[start : start + 4]
        l3_id = f"slc{cluster_index % l3_instances}"
        clusters.append(
            {
                "id": f"cluster{cluster_index}",
                "cores": cluster_cores,
                "l3": l3_id,
            }
        )
        cache_core_map[l3_id].extend(cluster_cores)

    size_bytes = l3_sets * l3_ways * l3_line_size
    caches = [
        {
            "id": cache_id,
            "level": "L3",
            "size_bytes": size_bytes,
            "line_size": l3_line_size,
            "sets": l3_sets,
            "ways": l3_ways,
            "monitor_group_sets": monitor_group_sets,
            "hit_latency_ns": l3_hit_latency_ns,
            "shared_by_cores": cache_core_map[cache_id],
        }
        for cache_id in cache_core_map
    ]
    memory_controllers = [
        {
            "id": f"mc{index}",
            "channels": channels_per_mc,
            "bandwidth_gbps_per_channel": channel_bandwidth_gbps,
            "scheduler": "priority_rr",
            "queue_depth": mc_queue_depth,
            "base_latency_ns": mc_base_latency_ns,
            "token_bucket_window_ns": 100,
            "aging_ns": 500,
            "cbusy_sample_ns": cbusy_sample_ns,
            "cbusy_feedback_latency_ns": cbusy_feedback_latency_ns,
            "cbusy_release_hold_samples": cbusy_release_hold_samples,
            "cbusy_l1_bw_ratio": cbusy_bw_ratios[0],
            "cbusy_l2_bw_ratio": cbusy_bw_ratios[1],
            "cbusy_l3_bw_ratio": cbusy_bw_ratios[2],
            "cbusy_l1_queue_ratio": cbusy_queue_ratios[0],
            "cbusy_l2_queue_ratio": cbusy_queue_ratios[1],
            "cbusy_l3_queue_ratio": cbusy_queue_ratios[2],
        }
        for index in range(mc_count)
    ]
    core_attach_nodes = {
        core: f"r{index % noc_routers}"
        for index, core in enumerate(cores)
    }
    cache_controls = [
        {
            "msc_id": f"slc{index}",
            "controls": [
                {
                    "partid": row["partid"],
                    "cmin": row["cmin"],
                    "cmax": row["cmax"],
                    "cpbm": row["cpbm"],
                    "cmin_enable": row["cmin_enable"],
                    "cmax_enable": row["cmax_enable"],
                    "cpbm_enable": row["cpbm_enable"],
                    "monitor_enable": row["monitor_enable"],
                }
                for row in partid_configs
            ],
        }
        for index in range(l3_instances)
    ]
    mc_controls = [
        {
            "msc_id": f"mc{index}",
            "controls": [
                {
                    "partid": row["partid"],
                    "bmin": row["bmin_gbps"],
                    "bmax": row["bmax_gbps"],
                    "bmin_enable": row["bmin_enable"],
                    "bmax_enable": row["bmax_enable"],
                    "limit_mode": row["limit_mode"],
                    "priority": row["priority"],
                    "priority_enable": row["priority_enable"],
                    "cbusy_enable": row["cbusy_enable"],
                    "cbusy_l1_ostd": row["cbusy_l1_ostd"],
                    "cbusy_l2_ostd": row["cbusy_l2_ostd"],
                    "cbusy_l3_ostd": row["cbusy_l3_ostd"],
                    "monitor_enable": row["monitor_enable"],
                }
                for row in partid_configs
            ],
        }
        for index in range(mc_count)
    ]
    protected_partids = sorted(
        {
            int(row["partid"])
            for row in stimulus_configs
            if row["enabled"] and row["target_p99_ns"] > 0
        }
    )
    active_partids = {
        int(row["partid"])
        for row in stimulus_configs
        if row["enabled"]
    }
    background_partids = sorted(
        active_partids - set(protected_partids)
    )

    return {
        "simulation": {
            "time_ns": duration_ns,
            "seed": seed,
            "control_interval_ns": control_interval_ns,
        },
        "soc": {
            "clusters": clusters,
            "core": {
                "threads_per_core": threads_per_core
            },
            "caches": caches,
            "noc": {
                "topology": "mesh",
                "routers": noc_routers,
                "link_bandwidth_gbps": noc_link_gbps,
                "router_latency_ns": noc_router_latency_ns,
                "queue_depth": noc_queue_depth,
                "virtual_channels": noc_virtual_channels,
                "average_hops": max(
                    1,
                    math.ceil(math.sqrt(noc_routers)) - 1,
                ),
            },
            "memory": {
                "controllers": memory_controllers
            },
        },
        "requesters": {
            "auto_expand_cpu_threads": True,
            "defaults": {
                "max_outstanding": max_outstanding
            },
            "core_attach_nodes": core_attach_nodes,
            "explicit": [],
        },
        "mpam": {
            "partid_width": 4,
            "pmg_width": 4,
            "partitions": [
                {
                    "partid": row["partid"],
                    "name": row["name"],
                }
                for row in partid_configs
            ],
            "msc_controls": cache_controls + mc_controls,
        },
        "workloads": workloads,
        "policies": [
            {
                "name": policy,
                "params": {
                    "interval_ns": control_interval_ns,
                    "max_bw_step_percent": max_bw_step,
                    "priority_min": 0,
                    "priority_max": 15,
                    "background_partids": background_partids,
                    "protected_partids": protected_partids,
                    "p99_hysteresis": hysteresis,
                    "min_hold_intervals": min_hold,
                },
            }
        ],
        "outputs": {
            "dir": output_dir,
            "formats": ["json", "csv"],
            "trace_requests": False,
            "visualization": {
                "generate_report": True,
                "report_format": "html",
                "plots": [
                    "latency",
                    "bandwidth",
                    "queue_occupancy",
                    "control_trace",
                    "topology",
                ],
            },
        },
    }
