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
            "cmin": 0,
            "cmax": ways,
            "cpbm": f"{full_mask:0{width}x}",
            "bmin_gbps": 0.0,
            "bmax_gbps": total_mc_bandwidth,
            "limit_mode": "softlimit",
            "priority": 4,
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


def default_parameters() -> Dict[str, object]:
    return {
        "duration_ns": 500_000,
        "control_interval_ns": 50_000,
        "seed": 1234,
        "active_cores": 8,
        "threads_per_core": 1,
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
        "protected_partid": 1,
        "protected_rate_mrps": 20,
        "protected_working_set_mb": 64,
        "protected_target_p99_ns": 500,
        "background_partid": 2,
        "background_cores": 7,
        "background_rate_gbps": 200,
        "background_rate_scope": "aggregate",
        "background_working_set_mb": 1024,
        "background_read_ratio": 0.8,
        "policy": "closed_loop_qos",
        "max_bw_step_percent": 10,
        "p99_hysteresis": 0.1,
        "min_hold_intervals": 3,
        "partid_configs": _default_partid_configs(),
    }


def _parse_partid_configs(
    parameters: Dict[str, object],
    ways: int,
    total_mc_bandwidth: float,
) -> List[Dict[str, object]]:
    raw_rows = parameters.get("partid_configs")
    if not isinstance(raw_rows, list) or len(raw_rows) != 16:
        raw_rows = _default_partid_configs(
            ways, total_mc_bandwidth
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
        parsed.append(
            {
                "partid": partid,
                "name": str(
                    raw.get("name", f"partid_{partid}")
                )[:32],
                "monitor_enable": bool(
                    raw.get("monitor_enable", True)
                ),
                "cmin": cmin,
                "cmax": cmax,
                "cpbm": cpbm,
                "bmin_gbps": bmin,
                "bmax_gbps": bmax,
                "limit_mode": limit_mode,
                "priority": priority,
            }
        )
    if seen != set(range(16)):
        raise ParameterError(
            "PARTID entries must cover every value 0..15"
        )
    return sorted(parsed, key=lambda row: row["partid"])


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
        values, "active_cores", 8, 2, 32
    )
    threads_per_core = _integer(
        values, "threads_per_core", 1, 1, 4
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
    total_mc_bandwidth = (
        channels_per_mc * channel_bandwidth_gbps
    )
    partid_configs = _parse_partid_configs(
        parameters,
        l3_ways,
        total_mc_bandwidth,
    )

    protected_partid = _integer(
        values, "protected_partid", 1, 0, 15
    )
    background_partid = _integer(
        values, "background_partid", 2, 0, 15
    )
    if protected_partid == background_partid:
        raise ParameterError(
            "Protected and background workloads need different PARTIDs"
        )
    protected_rate_mrps = _number(
        values, "protected_rate_mrps", 20, 0.01, 1000
    )
    protected_wss_mb = _integer(
        values,
        "protected_working_set_mb",
        64,
        1,
        65_536,
    )
    protected_target_p99_ns = _number(
        values,
        "protected_target_p99_ns",
        500,
        1,
        1_000_000,
    )
    background_cores = _integer(
        values,
        "background_cores",
        min(7, active_cores - 1),
        1,
        active_cores - 1,
    )
    background_rate_gbps = _number(
        values,
        "background_rate_gbps",
        200,
        0.01,
        4096,
    )
    background_scope = _choice(
        values,
        "background_rate_scope",
        "aggregate",
        ["aggregate", "per_requester"],
    )
    background_wss_mb = _integer(
        values,
        "background_working_set_mb",
        1024,
        1,
        262_144,
    )
    background_read_ratio = _number(
        values,
        "background_read_ratio",
        0.8,
        0,
        1,
    )

    interval_count = math.ceil(
        duration_ns / control_interval_ns
    )
    if interval_count > 1000:
        raise ParameterError(
            "duration_ns / control_interval_ns must not exceed 1000 intervals"
        )
    protected_requests = (
        duration_ns * protected_rate_mrps / 1000.0
    )
    requester_multiplier = (
        background_cores
        if background_scope == "per_requester"
        else 1
    )
    background_requests = (
        duration_ns
        * background_rate_gbps
        / (64.0 * 8.0)
        * requester_multiplier
    )
    if protected_requests + background_requests > 2_000_000:
        raise ParameterError(
            "Estimated request count exceeds 2,000,000; reduce duration, rate, or active requesters"
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
                    "limit_mode": row["limit_mode"],
                    "priority": row["priority"],
                    "monitor_enable": row["monitor_enable"],
                }
                for row in partid_configs
            ],
        }
        for index in range(mc_count)
    ]
    background_requesters = [
        f"cpu{index}.t0"
        for index in range(1, background_cores + 1)
    ]

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
        "workloads": [
            {
                "name": "latency_service",
                "type": "pointer_chase",
                "requesters": ["cpu0.t0"],
                "partid": protected_partid,
                "pmg": protected_partid,
                "request_size_bytes": 64,
                "injection_rate_mrps": protected_rate_mrps,
                "injection_scope": "aggregate",
                "read_ratio": 1.0,
                "working_set_bytes": (
                    protected_wss_mb * 1024 * 1024
                ),
                "target_p99_ns": protected_target_p99_ns,
            },
            {
                "name": "background_stream",
                "type": "stream",
                "requesters": background_requesters,
                "partid": background_partid,
                "pmg": background_partid,
                "request_size_bytes": 64,
                "injection_rate_gbps": background_rate_gbps,
                "injection_scope": background_scope,
                "read_ratio": background_read_ratio,
                "working_set_bytes": (
                    background_wss_mb * 1024 * 1024
                ),
            },
        ],
        "policies": [
            {
                "name": policy,
                "params": {
                    "interval_ns": control_interval_ns,
                    "max_bw_step_percent": max_bw_step,
                    "priority_min": 0,
                    "priority_max": 15,
                    "background_partids": [
                        background_partid
                    ],
                    "protected_partids": [
                        protected_partid
                    ],
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
