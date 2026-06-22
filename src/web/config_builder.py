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
            "cmin": 0.0,
            "cmax": 100.0,
            "cpbm": f"{full_mask:0{width}x}",
            "bmin_enable": True,
            "bmax_enable": True,
            "bmin_gbps": 0.0,
            "bmax_gbps": total_mc_bandwidth,
            "limit_mode": "softlimit",
            "mc_qos_enable": True,
            "mc_qos": 3,
            "cbusy_enable": False,
            "cbusy_l1_ostd": max(1, min(max_outstanding, math.ceil(max_outstanding * 0.75))),
            "cbusy_l2_ostd": max(1, min(max_outstanding, math.ceil(max_outstanding * 0.50))),
            "cbusy_l3_ostd": max(1, min(max_outstanding, math.ceil(max_outstanding * 0.125))),
        }
        rows.append(row)
    rows[0].update({"name": "default", "mc_qos": 3})
    rows[1].update(
        {
            "name": "latency_sensitive",
            "cmin": 25.0,
            "cmax": 50.0,
            "cpbm": f"{lower_mask:0{width}x}",
            "bmin_gbps": min(40.0, total_mc_bandwidth),
            "bmax_gbps": min(120.0, total_mc_bandwidth),
            "limit_mode": "hardlimit",
            "mc_qos": 7,
        }
    )
    rows[2].update(
        {
            "name": "background_bandwidth",
            "cmin": 0,
            "cmax": 50.0,
            "cpbm": f"{upper_mask:0{width}x}",
            "bmin_gbps": 0.0,
            "bmax_gbps": min(80.0, total_mc_bandwidth),
            "limit_mode": "hardlimit",
            "mc_qos": 2,
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
        "l3_miss_detect_latency_ns": 20,
        "l3_fill_latency_ns": 10,
        "l3_queue_depth": 128,
        "l3_lookup_parallelism": 16,
        "l3_mshr_entries": 64,
        "l3_fill_buffer_entries": 16,
        "l3_merge_same_line_misses": True,
        "l3_replacement_policy": "lru",
        "l3_clock_mhz": 1000,
        "l3_monitor_period_cycles": 256,
        "l3_history_weight": 192,
        "l3_current_weight": 64,
        "noc_routers": 8,
        "noc_link_gbps": 256,
        "noc_router_latency_ns": 5,
        "noc_queue_depth": 64,
        "noc_virtual_channels": 4,
        "noc_clock_mhz": 1000,
        "noc_flit_bytes": 16,
        "noc_link_slots_per_direction": 1,
        "noc_hop_latency_cycles": 1,
        "noc_tie_direction": "cw",
        "memory_controllers": 2,
        "channels_per_mc": 2,
        "channel_bandwidth_gbps": 128,
        "mc_base_latency_ns": 80,
        "mc_queue_depth": 512,
        "mc_interleave_mode": "linear",
        "mc_interleave_granularity_bytes": 256,
        "mc_interleave_xor_shift": 12,
        "mc_clock_mhz": 1000,
        "mc_monitor_period_cycles": 256,
        "mc_history_weight": 192,
        "mc_current_weight": 64,
        "mc_bandwidth_hysteresis": 0.05,
        "mc_aging_mode": "none",
        "mc_aging_quantum_cycles": 256,
        "mc_aging_counter_bits": 3,
        "mc_token_bucket_window_ns": 100,
        "mc_aging_ns": 500,
        "mc_qos_aging_max_steps": 3,
        "mc_bmin_qos_promote": 2,
        "mc_softlimit_qos_demote": 2,
        "max_outstanding": 32,
        "core_max_outstanding": 48,
        "core_ostd_policy": "shared",
        "thread_ostd_reserve": 8,
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
        reachable_percent = enabled_ways * 100.0 / ways
        cmin = float(raw.get("cmin", 0))
        cmax = float(raw.get("cmax", 100))
        if not 0 <= cmin <= cmax <= 100:
            raise ParameterError(
                f"PARTID {partid}: require 0 <= CMIN <= CMAX <= 100%"
            )
        if bool(raw.get("cmin_enable", True)) and cmin > reachable_percent + 1e-9:
            raise ParameterError(
                f"PARTID {partid}: enabled CMIN exceeds CPBM reachable capacity"
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
        mc_qos = int(raw.get("mc_qos", raw.get("priority", 3)))
        if not 0 <= mc_qos <= 7:
            raise ParameterError(
                f"PARTID {partid}: MC QoS must be 0..7"
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
                "mc_qos_enable": bool(
                    raw.get(
                        "mc_qos_enable",
                        raw.get("priority_enable", True),
                    )
                ),
                "mc_qos": mc_qos,
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
    enabled_cmin_total = sum(
        row["cmin"] for row in parsed if row["cmin_enable"]
    )
    if enabled_cmin_total > 100.0 + 1e-9:
        raise ParameterError(
            "Enabled L3 CMIN total must not exceed 100% per L3 instance"
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
                "dependency_mode": str(raw.get("dependency_mode", "independent")),
                "source_queue_depth": int(raw.get("source_queue_depth", 1)),
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
            "dependency_mode": row.get("dependency_mode", "independent"),
            "source_queue_depth": row.get("source_queue_depth", 1),
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
    l3_miss_detect_latency_ns = _number(
        values,
        "l3_miss_detect_latency_ns",
        20,
        1,
        500,
    )
    l3_fill_latency_ns = _number(
        values, "l3_fill_latency_ns", 10, 1, 500
    )
    l3_queue_depth = _integer(
        values, "l3_queue_depth", 128, 1, 8192
    )
    l3_lookup_parallelism = _integer(
        values, "l3_lookup_parallelism", 16, 1, 1024
    )
    l3_mshr_entries = _integer(
        values, "l3_mshr_entries", 64, 1, 8192
    )
    l3_fill_buffer_entries = _integer(
        values, "l3_fill_buffer_entries", 16, 1, 1024
    )
    l3_merge_same_line_misses = bool(
        values.get("l3_merge_same_line_misses", True)
    )
    l3_replacement_policy = _choice(
        values,
        "l3_replacement_policy",
        "lru",
        ["lru", "plru"],
    )
    if (
        l3_replacement_policy == "plru"
        and l3_ways & (l3_ways - 1)
    ):
        raise ParameterError(
            "PLRU requires l3_ways to be a power of two"
        )
    l3_clock_mhz = _number(
        values, "l3_clock_mhz", 1000, 1, 10_000
    )
    l3_monitor_period_cycles = _integer(
        values, "l3_monitor_period_cycles", 256, 1, 1_000_000
    )
    l3_history_weight = _integer(
        values, "l3_history_weight", 192, 0, 256
    )
    l3_current_weight = _integer(
        values, "l3_current_weight", 64, 0, 256
    )
    if l3_history_weight + l3_current_weight != 256:
        raise ParameterError(
            "L3 history_weight + current_weight must equal 256"
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
    noc_clock_mhz = _number(
        values, "noc_clock_mhz", 1000, 1, 10_000
    )
    noc_flit_bytes = _integer(
        values, "noc_flit_bytes", 16, 4, 256
    )
    noc_link_slots_per_direction = _integer(
        values,
        "noc_link_slots_per_direction",
        1,
        1,
        64,
    )
    noc_hop_latency_cycles = _integer(
        values,
        "noc_hop_latency_cycles",
        1,
        1,
        100,
    )
    noc_tie_direction = _choice(
        values,
        "noc_tie_direction",
        "cw",
        ["cw", "ccw"],
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
    mc_interleave_mode = _choice(
        values,
        "mc_interleave_mode",
        "linear",
        ["linear", "xor"],
    )
    mc_interleave_granularity_bytes = _integer(
        values,
        "mc_interleave_granularity_bytes",
        256,
        1,
        1 << 30,
    )
    if (
        mc_interleave_granularity_bytes
        & (mc_interleave_granularity_bytes - 1)
    ):
        raise ParameterError(
            "MC interleave granularity must be a power of two"
        )
    mc_interleave_xor_shift = _integer(
        values, "mc_interleave_xor_shift", 12, 0, 63
    )
    mc_clock_mhz = _number(
        values, "mc_clock_mhz", 1000, 1, 10_000
    )
    mc_monitor_period_cycles = _integer(
        values, "mc_monitor_period_cycles", 256, 1, 1_000_000
    )
    mc_history_weight = _integer(
        values, "mc_history_weight", 192, 0, 256
    )
    mc_current_weight = _integer(
        values, "mc_current_weight", 64, 0, 256
    )
    if mc_history_weight + mc_current_weight != 256:
        raise ParameterError(
            "MC history_weight + current_weight must equal 256"
        )
    mc_bandwidth_hysteresis = _number(
        values, "mc_bandwidth_hysteresis", 0.05, 0, 0.999999
    )
    mc_aging_mode = _choice(
        values,
        "mc_aging_mode",
        "none",
        ["none", "per_partid_service_deficit"],
    )
    mc_aging_quantum_cycles = _integer(
        values, "mc_aging_quantum_cycles", 256, 1, 1_000_000
    )
    mc_aging_counter_bits = _integer(
        values, "mc_aging_counter_bits", 3, 1, 16
    )
    mc_token_bucket_window_ns = _number(
        values, "mc_token_bucket_window_ns", 100, 0.1, 1_000_000
    )
    mc_aging_ns = _number(
        values, "mc_aging_ns", 500, 0.1, 1_000_000
    )
    mc_qos_aging_max_steps = _integer(
        values, "mc_qos_aging_max_steps", 3, 0, 7
    )
    mc_bmin_qos_promote = _integer(
        values, "mc_bmin_qos_promote", 2, 0, 7
    )
    mc_softlimit_qos_demote = _integer(
        values, "mc_softlimit_qos_demote", 2, 0, 7
    )
    max_outstanding = _integer(
        values, "max_outstanding", 32, 1, 1024
    )
    core_max_outstanding = _integer(
        values, "core_max_outstanding", 48, 1, 2048
    )
    core_ostd_policy = _choice(
        values,
        "core_ostd_policy",
        "shared",
        ["shared", "static_partition", "reserve_borrow"],
    )
    thread_ostd_reserve = _integer(
        values,
        "thread_ostd_reserve",
        8,
        1,
        core_max_outstanding,
    )
    if (
        core_ostd_policy == "reserve_borrow"
        and (
            thread_ostd_reserve > max_outstanding
            or thread_ostd_reserve * threads_per_core
            > core_max_outstanding
        )
    ):
        raise ParameterError(
            "reserve_borrow requires thread_ostd_reserve <= "
            "max_outstanding and total reserves <= "
            "core_max_outstanding"
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
            "miss_detect_latency_ns": (
                l3_miss_detect_latency_ns
            ),
            "fill_latency_ns": l3_fill_latency_ns,
            "queue_depth": l3_queue_depth,
            "lookup_parallelism": l3_lookup_parallelism,
            "mshr_entries": l3_mshr_entries,
            "fill_buffer_entries": l3_fill_buffer_entries,
            "merge_same_line_misses": (
                l3_merge_same_line_misses
            ),
            "replacement_policy": l3_replacement_policy,
            "clock_mhz": l3_clock_mhz,
            "monitor_period_cycles": l3_monitor_period_cycles,
            "history_weight": l3_history_weight,
            "current_weight": l3_current_weight,
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
            "clock_mhz": mc_clock_mhz,
            "monitor_period_cycles": mc_monitor_period_cycles,
            "history_weight": mc_history_weight,
            "current_weight": mc_current_weight,
            "bandwidth_hysteresis": mc_bandwidth_hysteresis,
            "aging_mode": mc_aging_mode,
            "aging_quantum_cycles": mc_aging_quantum_cycles,
            "aging_counter_bits": mc_aging_counter_bits,
            "token_bucket_window_ns": mc_token_bucket_window_ns,
            "aging_ns": mc_aging_ns,
            "qos_aging_max_steps": mc_qos_aging_max_steps,
            "bmin_qos_promote": mc_bmin_qos_promote,
            "softlimit_qos_demote": mc_softlimit_qos_demote,
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
                    "mc_qos": row["mc_qos"],
                    "mc_qos_enable": row["mc_qos_enable"],
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
                "topology": "three_bidirectional_bufferless_rings",
                "routers": noc_routers,
                "link_bandwidth_gbps": noc_link_gbps,
                "router_latency_ns": noc_router_latency_ns,
                "queue_depth": noc_queue_depth,
                "virtual_channels": noc_virtual_channels,
                "average_hops": max(
                    1,
                    math.ceil(math.sqrt(noc_routers)) - 1,
                ),
                "clock_mhz": noc_clock_mhz,
                "flit_bytes": noc_flit_bytes,
                "link_slots_per_direction": (
                    noc_link_slots_per_direction
                ),
                "hop_latency_cycles": noc_hop_latency_cycles,
                "tie_direction": noc_tie_direction,
                "ring_node_order": [
                    *(f"r{index}" for index in range(noc_routers)),
                    *(cache["id"] for cache in caches),
                    *(
                        controller["id"]
                        for controller in memory_controllers
                    ),
                ],
            },
            "memory": {
                "controllers": memory_controllers,
                "interleave": {
                    "mode": mc_interleave_mode,
                    "granularity_bytes": (
                        mc_interleave_granularity_bytes
                    ),
                    "xor_shift": mc_interleave_xor_shift,
                },
            },
        },
        "requesters": {
            "auto_expand_cpu_threads": True,
            "defaults": {
                "max_outstanding": max_outstanding,
                "core_max_outstanding": core_max_outstanding,
                "core_ostd_policy": core_ostd_policy,
                "thread_ostd_reserve": thread_ostd_reserve,
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
