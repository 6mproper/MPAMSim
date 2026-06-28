from __future__ import annotations

import copy
import math
from typing import Dict, List, Set, Tuple


DEFAULT_DURATION_NS = 5_000
DEFAULT_CONTROL_INTERVAL_NS = 128
MIN_DURATION_NS = 5_000
MIN_CONTROL_INTERVAL_NS = 128
DEFAULT_L3_SETS = 20 * 1024
DEFAULT_L3_WAYS = 20


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


def _boolean(
    values: Dict[str, object],
    name: str,
    default: bool,
) -> bool:
    value = values.get(name, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    raise ParameterError(f"{name} must be boolean")


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
    ways: int = DEFAULT_L3_WAYS,
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


def _hardware_threads(active_cores: int, threads_per_core: int) -> int:
    return active_cores * threads_per_core


def _thread_requester(slot: int, threads_per_core: int = 2) -> str:
    return f"cpu{slot // threads_per_core}.t{slot % threads_per_core}"


def _stimulus_defaults_for_type(workload_type: str) -> Dict[str, object]:
    mapping = {
        "stream": {
            "address_pattern": "sequential",
            "operation_mix": "read",
            "dependency_mode": "independent",
            "arrival_mode": "fixed",
            "issue_selection": "fifo",
            "independent_chains": 1,
        },
        "pointer_chase": {
            "address_pattern": "pointer_chase",
            "operation_mix": "read",
            "dependency_mode": "pointer_chain",
            "arrival_mode": "fixed",
            "issue_selection": "fifo",
            "independent_chains": 1,
        },
        "random_read": {
            "address_pattern": "uniform_random",
            "operation_mix": "read",
            "dependency_mode": "independent",
            "arrival_mode": "fixed",
            "issue_selection": "fifo",
            "independent_chains": 1,
        },
        "mixed_rw": {
            "address_pattern": "uniform_random",
            "operation_mix": "mixed",
            "dependency_mode": "independent",
            "arrival_mode": "fixed",
            "issue_selection": "eligible_scan",
            "independent_chains": 1,
        },
        "bursty_dma": {
            "address_pattern": "sequential",
            "operation_mix": "mixed",
            "dependency_mode": "independent",
            "arrival_mode": "burst",
            "issue_selection": "fifo",
            "independent_chains": 1,
        },
    }
    return dict(mapping.get(workload_type, mapping["stream"]))


def _default_stimulus_configs(
    active_cores: int = 8,
    threads_per_core: int = 2,
) -> List[Dict[str, object]]:
    rows = []
    workload_types = [
        "mixed_rw",
        "pointer_chase",
        "stream",
        "random_read",
    ]
    for slot in range(_hardware_threads(active_cores, threads_per_core)):
        workload_type = workload_types[slot % len(workload_types)]
        type_defaults = _stimulus_defaults_for_type(workload_type)
        row = {
            "slot": slot,
            "enabled": True,
            "requester": _thread_requester(slot, threads_per_core),
            "partid": slot % 16,
            "pmg": slot % 16,
            "request_qos": 0,
            "workload_type": workload_type,
            **type_defaults,
            "source_queue_depth": (
                4
                if type_defaults["issue_selection"] == "eligible_scan"
                else 1
            ),
            "eligible_scan_depth": (
                4
                if type_defaults["issue_selection"] == "eligible_scan"
                else 1
            ),
            "rate_value": 6.0,
            "rate_unit": "gbps",
            "request_size_bytes": 64,
            "read_ratio": (
                0.75 if workload_type == "mixed_rw" else 1.0
            ),
            "working_set_mb": (
                64 if workload_type == "pointer_chase" else 256
            ),
            "address_base_mb": slot * 256,
            "target_p99_ns": 0.0,
        }
        rows.append(row)
    if len(rows) > 1:
        rows[1].update(
            {
                "rate_value": 4.0,
                "rate_unit": "mrps",
                "working_set_mb": 64,
                "target_p99_ns": 500.0,
            }
        )
    if len(rows) > 2:
        rows[2].update(
            {
                "rate_value": 12.0,
                "rate_unit": "gbps",
                "working_set_mb": 1024,
                "read_ratio": 0.8,
            }
        )
    return rows


def _default_resctrl_groups(
    ways: int = DEFAULT_L3_WAYS,
    total_mc_bandwidth: float = 256.0,
) -> List[Dict[str, object]]:
    full_mask = (1 << ways) - 1
    lower_ways = max(1, ways // 2)
    lower_mask = (1 << lower_ways) - 1
    upper_mask = full_mask ^ lower_mask
    width = max(1, math.ceil(ways / 4))
    bandwidth_text = f"{total_mc_bandwidth:g}"
    return [
        {
            "enabled": True,
            "name": "root",
            "partid": 0,
            "mode": "shareable",
            "schemata": (
                f"L3:0={full_mask:0{width}x}\n"
                f"MB:0={bandwidth_text}"
            ),
            "tasks": "",
            "cpus": "0-15",
            "mb_limit_mode": "softlimit",
            "mon_groups": "",
        },
        {
            "enabled": True,
            "name": "latency",
            "partid": 1,
            "mode": "shareable",
            "schemata": (
                f"L3:0={lower_mask:0{width}x}\n"
                f"MB:0={min(120.0, total_mc_bandwidth):g}"
            ),
            "tasks": "thread_01",
            "cpus": "",
            "mb_limit_mode": "hardlimit",
            "mon_groups": "latency_mon|1|thread_01|",
        },
        {
            "enabled": True,
            "name": "background",
            "partid": 2,
            "mode": "shareable",
            "schemata": (
                f"L3:0={upper_mask:0{width}x}\n"
                f"MB:0={min(80.0, total_mc_bandwidth):g}"
            ),
            "tasks": "thread_02,thread_03",
            "cpus": "",
            "mb_limit_mode": "hardlimit",
            "mon_groups": "background_mon|1|thread_02,thread_03|",
        },
    ]


def _parse_range_tokens(
    text: object,
    maximum: int,
    label: str,
) -> Set[int]:
    result: Set[int] = set()
    for raw_token in str(text or "").replace(";", ",").split(","):
        token = raw_token.strip()
        if not token:
            continue
        if "-" in token:
            left_text, right_text = token.split("-", 1)
            left = int(left_text.strip())
            right = int(right_text.strip())
            if right < left:
                raise ParameterError(f"{label} range is inverted: {token}")
            values = range(left, right + 1)
        else:
            values = (int(token),)
        for value in values:
            if not 0 <= value <= maximum:
                raise ParameterError(
                    f"{label} value {value} is outside 0..{maximum}"
                )
            result.add(value)
    return result


def _task_slot_from_token(token: str, threads_per_core: int) -> int:
    text = token.strip()
    if text.startswith("thread_"):
        return int(text.removeprefix("thread_"))
    if text.startswith("thread"):
        return int(text.removeprefix("thread"))
    if text.startswith("cpu") and ".t" in text:
        core_text, thread_text = text.removeprefix("cpu").split(".t", 1)
        return int(core_text) * threads_per_core + int(thread_text)
    return int(text)


def _parse_task_slots(
    text: object,
    active_cores: int,
    threads_per_core: int,
) -> Set[int]:
    result: Set[int] = set()
    max_slot = _hardware_threads(active_cores, threads_per_core) - 1
    for raw_token in str(text or "").replace(";", ",").split(","):
        token = raw_token.strip()
        if not token:
            continue
        if "-" in token and token.replace("-", "").replace("_", "").isdigit():
            result.update(_parse_range_tokens(token, max_slot, "resctrl task"))
            continue
        slot = _task_slot_from_token(token, threads_per_core)
        if not 0 <= slot <= max_slot:
            raise ParameterError(
                f"resctrl task {token} maps outside thread_00..thread_{max_slot:02d}"
            )
        result.add(slot)
    return result


def _parse_schemata(
    text: object,
    ways: int,
    total_mc_bandwidth: float,
) -> Tuple[Dict[int, str], Dict[int, float]]:
    l3_domains: Dict[int, str] = {}
    mb_domains: Dict[int, float] = {}
    full_mask = (1 << ways) - 1
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ParameterError(
                f"resctrl schemata line missing resource type: {line}"
            )
        resource, assignments = line.split(":", 1)
        resource = resource.strip().upper()
        if resource not in {"L3", "MB"}:
            raise ParameterError(
                f"resctrl resource {resource} is not supported in this phase"
            )
        for raw_assignment in assignments.split(";"):
            assignment = raw_assignment.strip()
            if not assignment:
                continue
            if "=" not in assignment:
                raise ParameterError(
                    f"resctrl schemata assignment missing '=': {assignment}"
                )
            domain_text, value_text = assignment.split("=", 1)
            domain = int(domain_text.strip())
            if domain < 0:
                raise ParameterError("resctrl domain id must be non-negative")
            if resource == "L3":
                l3_domains[domain] = _mask(
                    value_text.strip(),
                    ways,
                    full_mask,
                )
            else:
                value = float(value_text.strip())
                if not 0 <= value <= total_mc_bandwidth:
                    raise ParameterError(
                        "resctrl MB schema must be in per-MC Gbps range"
                    )
                mb_domains[domain] = value
    return l3_domains, mb_domains


def _domain_values(
    values: Dict[int, object],
    count: int,
) -> Dict[int, object]:
    if not values:
        return {}
    fallback = values.get(0)
    result: Dict[int, object] = {}
    for index in range(count):
        if index in values:
            result[index] = values[index]
        elif fallback is not None:
            result[index] = fallback
    return result


def _parse_resctrl_mon_groups(
    raw: object,
    active_cores: int,
    threads_per_core: int,
) -> List[Dict[str, object]]:
    if isinstance(raw, list):
        rows = raw
    else:
        rows = []
        for raw_line in str(raw or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split("|")]
            while len(parts) < 4:
                parts.append("")
            rows.append(
                {
                    "name": parts[0],
                    "pmg": parts[1],
                    "tasks": parts[2],
                    "cpus": parts[3],
                }
            )
    parsed = []
    seen_names = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ParameterError("resctrl MON group must be an object")
        name = str(row.get("name", f"mon{index}")).strip()
        if not name or "/" in name or name in seen_names:
            raise ParameterError("resctrl MON group names must be unique")
        seen_names.add(name)
        pmg = int(row.get("pmg", index + 1))
        if not 0 <= pmg <= 15:
            raise ParameterError("resctrl MON group PMG must be 0..15")
        parsed.append(
            {
                "name": name[:32],
                "pmg": pmg,
                "task_slots": _parse_task_slots(
                    row.get("tasks", ""),
                    active_cores,
                    threads_per_core,
                ),
                "cpu_slots": _parse_range_tokens(
                    row.get("cpus", ""),
                    _hardware_threads(active_cores, threads_per_core) - 1,
                    "resctrl MON cpus_list",
                ),
            }
        )
    return parsed


def _parse_resctrl_groups(
    raw_groups: object,
    ways: int,
    total_mc_bandwidth: float,
    l3_instances: int,
    mc_count: int,
    active_cores: int,
    threads_per_core: int,
) -> List[Dict[str, object]]:
    groups = raw_groups if isinstance(raw_groups, list) else []
    if not groups:
        groups = _default_resctrl_groups(ways, total_mc_bandwidth)
    parsed = []
    used_partids = set()
    seen_names = set()
    for index, raw in enumerate(groups):
        if not isinstance(raw, dict):
            raise ParameterError("Each resctrl group must be an object")
        name = str(raw.get("name", f"group{index}")).strip()
        if not name or "/" in name or name in seen_names:
            raise ParameterError("resctrl group names must be unique")
        seen_names.add(name)
        enabled = bool(raw.get("enabled", True)) or name == "root"
        if not enabled:
            continue
        partid = int(raw.get("partid", index))
        if partid < 0 or partid > 15 or partid in used_partids:
            raise ParameterError(
                "resctrl CTRL_MON groups require unique PARTID 0..15"
            )
        used_partids.add(partid)
        mode = str(raw.get("mode", "shareable"))
        if mode not in {"shareable", "exclusive"}:
            raise ParameterError(
                "resctrl mode supports shareable or exclusive in this phase"
            )
        limit_mode = str(raw.get("mb_limit_mode", "softlimit"))
        if limit_mode not in {"softlimit", "hardlimit"}:
            raise ParameterError(
                "resctrl MB limit mode must be softlimit or hardlimit"
            )
        l3_schema, mb_schema = _parse_schemata(
            raw.get("schemata", ""),
            ways,
            total_mc_bandwidth,
        )
        parsed.append(
            {
                "name": name[:32],
                "partid": partid,
                "mode": mode,
                "mb_limit_mode": limit_mode,
                "task_slots": _parse_task_slots(
                    raw.get("tasks", ""),
                    active_cores,
                    threads_per_core,
                ),
                "cpu_slots": _parse_range_tokens(
                    raw.get("cpus", ""),
                    _hardware_threads(active_cores, threads_per_core) - 1,
                    "resctrl cpus_list",
                ),
                "l3_cpbm_by_domain": _domain_values(
                    l3_schema,
                    l3_instances,
                ),
                "mc_bmax_by_domain": _domain_values(
                    mb_schema,
                    mc_count,
                ),
                "mon_groups": _parse_resctrl_mon_groups(
                    raw.get("mon_groups", ""),
                    active_cores,
                    threads_per_core,
                ),
            }
        )
    if not any(group["name"] == "root" for group in parsed):
        full_mask = (1 << ways) - 1
        width = max(1, math.ceil(ways / 4))
        parsed.insert(
            0,
            {
                "name": "root",
                "partid": 0,
                "mode": "shareable",
                "mb_limit_mode": "softlimit",
                "task_slots": set(),
                "cpu_slots": set(
                    range(_hardware_threads(active_cores, threads_per_core))
                ),
                "l3_cpbm_by_domain": {
                    index: f"{full_mask:0{width}x}"
                    for index in range(l3_instances)
                },
                "mc_bmax_by_domain": {
                    index: total_mc_bandwidth
                    for index in range(mc_count)
                },
                "mon_groups": [],
            },
        )
    return parsed


def _apply_resctrl_groups(
    values: Dict[str, object],
    ways: int,
    total_mc_bandwidth: float,
    max_outstanding: int,
    l3_instances: int,
    mc_count: int,
    active_cores: int,
    threads_per_core: int,
) -> Dict[str, object]:
    if not bool(values.get("resctrl_enabled", False)):
        return values
    translated = dict(values)
    partid_rows = copy.deepcopy(
        values.get("partid_configs")
        if isinstance(values.get("partid_configs"), list)
        else _default_partid_configs(ways, total_mc_bandwidth, max_outstanding)
    )
    stimulus_rows = copy.deepcopy(
        _normalize_stimulus_configs(
            values.get("stimulus_configs"),
            active_cores,
            threads_per_core,
        )
    )
    groups = _parse_resctrl_groups(
        values.get("resctrl_groups"),
        ways,
        total_mc_bandwidth,
        l3_instances,
        mc_count,
        active_cores,
        threads_per_core,
    )
    root = next(
        (group for group in groups if group["name"] == "root"),
        groups[0],
    )
    task_groups: Dict[int, Dict[str, object]] = {}
    cpu_groups: Dict[int, Dict[str, object]] = {}
    for group in groups:
        for slot in group["task_slots"]:
            if slot in task_groups:
                raise ParameterError(
                    f"resctrl task thread_{slot:02d} appears in multiple groups"
                )
            task_groups[slot] = group
        if group["name"] == "root":
            continue
        for slot in group["cpu_slots"]:
            if slot in cpu_groups:
                raise ParameterError(
                    f"resctrl CPU {slot} appears in multiple non-root groups"
                )
            cpu_groups[slot] = group

    rows_by_partid = {
        int(row.get("partid", index)): row
        for index, row in enumerate(partid_rows)
        if isinstance(row, dict)
    }
    full_mask = (1 << ways) - 1
    width = max(1, math.ceil(ways / 4))
    for group in groups:
        partid = int(group["partid"])
        row = rows_by_partid.setdefault(
            partid,
            {"partid": partid, "name": f"partid_{partid}"},
        )
        l3_domains = group["l3_cpbm_by_domain"]
        mc_domains = group["mc_bmax_by_domain"]
        row.update(
            {
                "name": group["name"],
                "monitor_enable": True,
                "cpbm_enable": bool(l3_domains),
                "cmin_enable": False,
                "cmax_enable": False,
                "cmin": 0.0,
                "cmax": 100.0,
                "cpbm": (
                    str(l3_domains.get(0))
                    if l3_domains
                    else f"{full_mask:0{width}x}"
                ),
                "l3_cpbm_by_domain": l3_domains,
                "bmin_enable": False,
                "bmax_enable": bool(mc_domains),
                "bmin_gbps": 0.0,
                "bmax_gbps": (
                    float(mc_domains.get(0))
                    if mc_domains
                    else total_mc_bandwidth
                ),
                "mc_bmax_by_domain": mc_domains,
                "limit_mode": group["mb_limit_mode"],
                "mc_qos_enable": False,
                "mc_qos": 3,
                "cbusy_enable": False,
                "cbusy_l1_ostd": max(
                    1,
                    min(
                        max_outstanding,
                        math.ceil(max_outstanding * 0.75),
                    ),
                ),
                "cbusy_l2_ostd": max(
                    1,
                    min(
                        max_outstanding,
                        math.ceil(max_outstanding * 0.50),
                    ),
                ),
                "cbusy_l3_ostd": max(
                    1,
                    min(
                        max_outstanding,
                        math.ceil(max_outstanding * 0.125),
                    ),
                ),
            }
        )

    def monitor_pmg_for(group: Dict[str, object], slot: int) -> int:
        for mon_group in group["mon_groups"]:
            if (
                slot in mon_group["task_slots"]
                or slot in mon_group["cpu_slots"]
            ):
                return int(mon_group["pmg"])
        return 0

    for index, row in enumerate(stimulus_rows):
        if not isinstance(row, dict):
            continue
        slot = int(row.get("slot", index))
        group = task_groups.get(slot) or cpu_groups.get(slot) or root
        row["partid"] = int(group["partid"])
        row["pmg"] = monitor_pmg_for(group, slot)

    translated["partid_configs"] = partid_rows
    translated["stimulus_configs"] = stimulus_rows
    return translated


def _normalize_stimulus_configs(
    raw_rows: object,
    active_cores: int,
    threads_per_core: int,
) -> List[Dict[str, object]]:
    defaults = _default_stimulus_configs(active_cores, threads_per_core)
    if not isinstance(raw_rows, list):
        return defaults
    rows_by_slot: Dict[int, Dict[str, object]] = {}
    for index, raw in enumerate(raw_rows):
        if not isinstance(raw, dict):
            continue
        try:
            slot = int(raw.get("slot", index))
        except (TypeError, ValueError):
            continue
        rows_by_slot[slot] = copy.deepcopy(raw)
    normalized = []
    for slot, default_row in enumerate(defaults):
        row = {**default_row, **rows_by_slot.get(slot, {})}
        row["slot"] = slot
        row["requester"] = _thread_requester(slot, threads_per_core)
        row["partid"] = int(row.get("partid", slot % 16)) % 16
        row["pmg"] = int(row.get("pmg", slot % 16)) % 16
        normalized.append(row)
    return normalized


def default_parameters() -> Dict[str, object]:
    return {
        "duration_ns": DEFAULT_DURATION_NS,
        "control_interval_ns": DEFAULT_CONTROL_INTERVAL_NS,
        "seed": 1234,
        "active_cores": 8,
        "threads_per_core": 2,
        "l3_instances": 2,
        "l3_sets": DEFAULT_L3_SETS,
        "l3_ways": DEFAULT_L3_WAYS,
        "l3_line_size": 64,
        "l3_monitor_group_sets": 8,
        "l3_sampling_mode": "fixed_first",
        "l3_sampling_rotation_period_monitor_cycles": 1,
        "l3_hit_latency_ns": 20,
        "l3_miss_detect_latency_ns": 20,
        "l3_fill_latency_ns": 10,
        "l3_queue_depth": 128,
        "l3_lookup_parallelism": 16,
        "l3_mshr_entries": 64,
        "l3_fill_buffer_entries": 16,
        "l3_merge_same_line_misses": False,
        "l3_replacement_policy": "lru",
        "l3_clock_mhz": 1000,
        "l3_monitor_period_cycles": 256,
        "l3_history_weight": 0.75,
        "l3_current_weight": 0.25,
        "l3_qos_scheduler_enable": False,
        "l3_cbusy_qos_demote_per_level": 1,
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
        "mc_history_weight": 0.95,
        "mc_current_weight": 0.05,
        "mc_bandwidth_hysteresis": 0.05,
        "mc_aging_mode": "none",
        "mc_aging_quantum_cycles": 256,
        "mc_aging_counter_bits": 3,
        "mc_token_bucket_window_ns": 100,
        "mc_aging_ns": 500,
        "mc_qos_aging_max_steps": 3,
        "mc_qos_adjust_mode": "fixed_step",
        "mc_bmin_qos_promote": 2,
        "mc_softlimit_qos_demote": 2,
        "mc_bmin_error_weight": 4.0,
        "mc_bmax_error_weight": 4.0,
        "mc_qos_error_deadband_percent": 5.0,
        "mc_qos_error_max_delta": 2,
        "mc_qos_error_quantization": "threshold_lut",
        "mc_qos_combiner_order": "adjust_after_request_combine",
        "mc_qos_combine_op": "replace",
        "mc_qos_map_8_to_4_enable": False,
        "max_outstanding": 32,
        "core_max_outstanding": 48,
        "core_ostd_policy": "shared",
        "thread_ostd_reserve": 8,
        "cbusy_sample_ns": 1_000,
        "cbusy_feedback_latency_ns": 50,
        "cbusy_release_hold_samples": 3,
        "cpu_cbusy_response_enable": False,
        "l3_cbusy_response_enable": False,
        "cbusy_l1_bw_ratio": 1.0,
        "cbusy_l2_bw_ratio": 1.1,
        "cbusy_l3_bw_ratio": 1.25,
        "cbusy_l1_queue_ratio": 0.25,
        "cbusy_l2_queue_ratio": 0.50,
        "cbusy_l3_queue_ratio": 0.75,
        "policy": "static_mpam",
        "resctrl_enabled": False,
        "resctrl_groups": _default_resctrl_groups(
            DEFAULT_L3_WAYS,
            2 * 128.0,
        ),
        "partid_configs": _default_partid_configs(DEFAULT_L3_WAYS),
        "stimulus_configs": _default_stimulus_configs(),
    }


def _disable_all_stimulus(parameters: Dict[str, object]) -> None:
    for row in parameters["stimulus_configs"]:
        row["enabled"] = False
        row["target_p99_ns"] = 0.0


def _disable_all_controls(parameters: Dict[str, object]) -> None:
    for row in parameters["partid_configs"]:
        row.update(
            {
                "monitor_enable": True,
                "cpbm_enable": False,
                "cmin_enable": False,
                "cmax_enable": False,
                "bmin_enable": False,
                "bmax_enable": False,
                "mc_qos_enable": False,
                "cbusy_enable": False,
                "cmin": 0.0,
                "cmax": 100.0,
                "bmin_gbps": 0.0,
                "bmax_gbps": 256.0,
                "limit_mode": "softlimit",
                "mc_qos": 3,
            }
        )


def _set_all_cpbm(parameters: Dict[str, object], cpbm: str) -> None:
    for row in parameters["partid_configs"]:
        row["cpbm"] = cpbm


def _apply_stimulus(
    parameters: Dict[str, object],
    slot: int,
    partid: int,
    rate_value: float,
    workload_type: str = "random_read",
    rate_unit: str = "gbps",
    working_set_mb: int = 64,
    read_ratio: float = 1.0,
    target_p99_ns: float = 0.0,
    address_base_mb: int = 0,
    request_qos: int = 0,
) -> None:
    row = parameters["stimulus_configs"][slot]
    type_defaults = _stimulus_defaults_for_type(workload_type)
    row.update(
        {
            "enabled": True,
            "partid": partid,
            "pmg": partid,
            "request_qos": request_qos,
            "workload_type": workload_type,
            **type_defaults,
            "source_queue_depth": (
                4
                if type_defaults["issue_selection"] == "eligible_scan"
                else 1
            ),
            "eligible_scan_depth": (
                4
                if type_defaults["issue_selection"] == "eligible_scan"
                else 1
            ),
            "rate_value": rate_value,
            "rate_unit": rate_unit,
            "request_size_bytes": 64,
            "read_ratio": read_ratio,
            "working_set_mb": working_set_mb,
            "address_base_mb": address_base_mb,
            "target_p99_ns": target_p99_ns,
        }
    )


def _preset_base() -> Dict[str, object]:
    parameters = copy.deepcopy(default_parameters())
    parameters.update(
        {
            "duration_ns": DEFAULT_DURATION_NS,
            "control_interval_ns": DEFAULT_CONTROL_INTERVAL_NS,
            "policy": "static_mpam",
            "memory_controllers": 1,
            "channels_per_mc": 1,
            "channel_bandwidth_gbps": 16,
            "mc_base_latency_ns": 250,
            "mc_queue_depth": 48,
            "max_outstanding": 32,
            "core_max_outstanding": 48,
            "cbusy_sample_ns": 500,
            "cbusy_feedback_latency_ns": 10,
            "cbusy_release_hold_samples": 3,
            "cbusy_l1_queue_ratio": 0.04,
            "cbusy_l2_queue_ratio": 0.08,
            "cbusy_l3_queue_ratio": 0.14,
            "cbusy_l1_bw_ratio": 0.80,
            "cbusy_l2_bw_ratio": 1.00,
            "cbusy_l3_bw_ratio": 1.20,
            "mc_aging_mode": "per_partid_service_deficit",
            "mc_qos_aging_max_steps": 2,
        }
    )
    _disable_all_stimulus(parameters)
    _disable_all_controls(parameters)
    return parameters


def control_effect_presets() -> List[Dict[str, object]]:
    """Return synthetic, deterministic UI presets that expose control effects."""
    presets: List[Dict[str, object]] = []

    hard_cbusy = _preset_base()
    hard_cbusy.update(
        {
            "cpu_cbusy_response_enable": True,
            "l3_cbusy_response_enable": True,
        }
    )
    _apply_stimulus(hard_cbusy, 0, 0, 500, "random_read", "mrps")
    hard_cbusy["partid_configs"][0].update(
        {
            "name": "partid0_hard_bmax_cbusy",
            "bmax_enable": True,
            "bmax_gbps": 4.0,
            "limit_mode": "hardlimit",
            "cbusy_enable": True,
            "cbusy_l1_ostd": 8,
            "cbusy_l2_ostd": 4,
            "cbusy_l3_ostd": 2,
        }
    )
    presets.append(
        {
            "id": "mc_hard_bmax_cbusy",
            "name": "MC hard BMAX + CBusy",
            "summary": "单PARTID高压随机读，触发MC hard BMAX和返回侧CBusy源端OSTD限制。",
            "expected": "控制总览应看到MC hard/over状态、CBusy L1-L3、CPU effective OSTD低于configured。",
            "parameters": hard_cbusy,
        }
    )

    qos_bmin = _preset_base()
    qos_bmin.update(
        {
            "mc_queue_depth": 64,
            "mc_bmin_qos_promote": 2,
            "mc_softlimit_qos_demote": 2,
        }
    )
    _apply_stimulus(qos_bmin, 0, 0, 32, "stream", address_base_mb=0)
    _apply_stimulus(qos_bmin, 2, 1, 32, "stream", address_base_mb=1024)
    qos_bmin["partid_configs"][0].update(
        {
            "name": "partid0_bmin_qos",
            "cpbm_enable": True,
            "cmax_enable": True,
            "cpbm": "0000",
            "cmax": 0.0,
            "bmin_enable": True,
            "bmin_gbps": 6.0,
            "bmax_enable": True,
            "bmax_gbps": 14.0,
            "limit_mode": "softlimit",
            "mc_qos_enable": True,
            "mc_qos": 4,
        }
    )
    qos_bmin["partid_configs"][1].update(
        {
            "name": "partid1_background",
            "cpbm_enable": True,
            "cmax_enable": True,
            "cpbm": "0000",
            "cmax": 0.0,
            "mc_qos_enable": True,
            "mc_qos": 2,
            "bmax_enable": True,
            "bmax_gbps": 16.0,
            "limit_mode": "softlimit",
        }
    )
    presets.append(
        {
            "id": "mc_bmin_qos_compete",
            "name": "MC BMIN / QoS 竞争",
            "summary": "两个PARTID使用不同地址窗口同时打满MC，PARTID 0通过BMIN和3-bit QoS获得调度偏好。",
            "expected": "控制总览应看到PARTID 0 effective QoS高于背景流，PARTID 0/1都产生MC带宽归因。",
            "parameters": qos_bmin,
        }
    )

    l3_pressure = _preset_base()
    l3_pressure.update(
        {
            "l3_instances": 1,
            "l3_sets": 128,
            "l3_ways": 8,
            "l3_queue_depth": 64,
            "channel_bandwidth_gbps": 64,
        }
    )
    _set_all_cpbm(l3_pressure, "ff")
    _apply_stimulus(
        l3_pressure, 0, 0, 120, "random_read", "gbps", 128,
        address_base_mb=0,
    )
    _apply_stimulus(
        l3_pressure, 1, 1, 120, "random_read", "gbps", 128,
        address_base_mb=512,
    )
    l3_pressure["partid_configs"][0].update(
        {
            "name": "partid0_cmin_protected",
            "cpbm_enable": True,
            "cmin_enable": True,
            "cmax_enable": True,
            "cmin": 40.0,
            "cmax": 100.0,
            "cpbm": "ff",
        }
    )
    l3_pressure["partid_configs"][1].update(
        {
            "name": "partid1_cmax_limited",
            "cpbm_enable": True,
            "cmax_enable": True,
            "cmax": 15.0,
            "cpbm": "ff",
        }
    )
    presets.append(
        {
            "id": "l3_cmin_cmax_pressure",
            "name": "L3 CMIN / CMAX 压力",
            "summary": "小L3容量下两个随机读PARTID互相竞争，突出CMIN保护和CMAX增长限制。",
            "expected": "控制总览应看到L3 filtered/actual差异、allocation denial或替换压力。",
            "parameters": l3_pressure,
        }
    )

    mixed = _preset_base()
    mixed.update(
        {
            "l3_instances": 1,
            "l3_sets": 1024,
            "l3_ways": 8,
            "cpu_cbusy_response_enable": True,
            "l3_cbusy_response_enable": True,
            "channel_bandwidth_gbps": 24,
            "mc_queue_depth": 64,
        }
    )
    _set_all_cpbm(mixed, "ff")
    _apply_stimulus(
        mixed, 0, 0, 96, "random_read", "gbps", 128, 1.0, 350.0,
        address_base_mb=0,
    )
    _apply_stimulus(mixed, 1, 1, 96, "stream", address_base_mb=512)
    _apply_stimulus(
        mixed, 2, 2, 96, "mixed_rw", "gbps", 256, 0.7,
        address_base_mb=1024,
    )
    mixed["policy"] = "static_mpam"
    mixed["partid_configs"][0].update(
        {
            "name": "partid0_protected",
            "cpbm_enable": True,
            "cmin_enable": True,
            "cmax_enable": True,
            "cmin": 30.0,
            "cmax": 70.0,
            "bmin_enable": True,
            "bmin_gbps": 8.0,
            "bmax_enable": True,
            "bmax_gbps": 14.0,
            "limit_mode": "softlimit",
            "mc_qos_enable": True,
            "mc_qos": 7,
            "cbusy_enable": True,
            "cbusy_l1_ostd": 10,
            "cbusy_l2_ostd": 5,
            "cbusy_l3_ostd": 2,
        }
    )
    for partid in (1, 2):
        mixed["partid_configs"][partid].update(
            {
                "name": f"partid{partid}_background",
                "cpbm_enable": True,
                "cmax_enable": True,
                "cmax": 45.0,
                "bmax_enable": True,
                "bmax_gbps": 10.0,
                "limit_mode": "softlimit",
                "mc_qos_enable": True,
                "mc_qos": 1,
            }
        )
    presets.append(
        {
            "id": "mixed_control_overview",
            "name": "混合控制总览压力",
            "summary": "PARTID 0保护流叠加两个背景流，用于同时观察CPU OSTD、L3和MC控制状态。",
            "expected": "控制总览矩阵应出现多个PARTID状态，PARTID 0曲线显示目标带、filtered监控和控制事件。",
            "parameters": mixed,
        }
    )

    return presets


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
                "l3_cpbm_by_domain": dict(
                    raw.get("l3_cpbm_by_domain", {})
                ),
                "bmin_enable": bool(raw.get("bmin_enable", True)),
                "bmax_enable": bool(raw.get("bmax_enable", True)),
                "bmin_gbps": bmin,
                "bmax_gbps": bmax,
                "mc_bmax_by_domain": dict(
                    raw.get("mc_bmax_by_domain", {})
                ),
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
    active_cores: int = 8,
    threads_per_core: int = 2,
) -> List[Dict[str, object]]:
    raw_rows = parameters.get("stimulus_configs")
    expected_slots = _hardware_threads(active_cores, threads_per_core)
    if not isinstance(raw_rows, list) or len(raw_rows) != expected_slots:
        raise ParameterError(
            "stimulus_configs must contain exactly "
            f"{expected_slots} thread rows"
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
        if slot < 0 or slot >= expected_slots or slot in seen:
            raise ParameterError(
                "Stimulus slots must uniquely cover "
                f"0..{expected_slots - 1}"
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
        type_defaults = _stimulus_defaults_for_type(workload_type)
        address_pattern = str(
            raw.get(
                "address_pattern",
                type_defaults["address_pattern"],
            )
        )
        operation_mix = str(
            raw.get(
                "operation_mix",
                type_defaults["operation_mix"],
            )
        )
        dependency_mode = str(
            raw.get(
                "dependency_mode",
                type_defaults["dependency_mode"],
            )
        )
        arrival_mode = str(
            raw.get("arrival_mode", type_defaults["arrival_mode"])
        )
        issue_selection = str(
            raw.get(
                "issue_selection",
                type_defaults["issue_selection"],
            )
        )
        rate_unit = str(raw.get("rate_unit", "gbps")).lower()
        if rate_unit not in {"mrps", "gbps"}:
            raise ParameterError(
                f"Stimulus {slot}: rate unit must be mrps or gbps"
            )
        try:
            rate_value = float(raw.get("rate_value", 0.0))
            request_size = int(raw.get("request_size_bytes", 64))
            request_qos = int(
                raw.get("request_qos", raw.get("qos_class", 0))
            )
            read_ratio = float(raw.get("read_ratio", 1.0))
            working_set_mb = int(raw.get("working_set_mb", 64))
            address_base_mb = int(raw.get("address_base_mb", 0))
            target_p99 = float(raw.get("target_p99_ns", 0.0) or 0.0)
            source_queue_depth = int(
                raw.get("source_queue_depth", 1)
            )
            independent_chains = int(
                raw.get(
                    "independent_chains",
                    type_defaults["independent_chains"],
                )
            )
            eligible_scan_depth = int(
                raw.get(
                    "eligible_scan_depth",
                    min(4, source_queue_depth),
                )
            )
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
        if not 0 <= request_qos <= 7:
            raise ParameterError(
                f"Stimulus {slot}: request QoS must be 0..7"
            )
        if not 0.0 <= read_ratio <= 1.0:
            raise ParameterError(
                f"Stimulus {slot}: read ratio must be in [0, 1]"
            )
        if not 1 <= working_set_mb <= 262_144:
            raise ParameterError(
                f"Stimulus {slot}: working set must be 1..262144 MB"
            )
        if not 0 <= address_base_mb <= 1_048_576:
            raise ParameterError(
                f"Stimulus {slot}: address base must be 0..1048576 MB"
            )
        if not 0.0 <= target_p99 <= 1_000_000:
            raise ParameterError(
                f"Stimulus {slot}: target P99 must be 0..1000000 ns"
            )
        if address_pattern not in {
            "sequential",
            "uniform_random",
            "pointer_chase",
            "stride",
            "hotset",
        }:
            raise ParameterError(
                f"Stimulus {slot}: unsupported address pattern"
            )
        if operation_mix not in {"read", "write", "mixed"}:
            raise ParameterError(
                f"Stimulus {slot}: operation mix must be read, write, or mixed"
            )
        if dependency_mode not in {"independent", "pointer_chain"}:
            raise ParameterError(
                f"Stimulus {slot}: dependency mode must be independent or pointer_chain"
            )
        if arrival_mode not in {"fixed", "poisson", "burst"}:
            raise ParameterError(
                f"Stimulus {slot}: arrival mode must be fixed, poisson, or burst"
            )
        if issue_selection not in {"fifo", "eligible_scan"}:
            raise ParameterError(
                f"Stimulus {slot}: issue selection must be fifo or eligible_scan"
            )
        if not 1 <= independent_chains <= 1024:
            raise ParameterError(
                f"Stimulus {slot}: independent chains must be 1..1024"
            )
        if not 1 <= source_queue_depth <= 4096:
            raise ParameterError(
                f"Stimulus {slot}: source queue depth must be 1..4096"
            )
        if not 1 <= eligible_scan_depth <= source_queue_depth:
            raise ParameterError(
                f"Stimulus {slot}: eligible scan depth must be in [1, source_queue_depth]"
            )
        if dependency_mode == "pointer_chain" and operation_mix == "write":
            raise ParameterError(
                f"Stimulus {slot}: pointer_chain requires read traffic"
            )
        parsed.append(
            {
                "slot": slot,
                "enabled": enabled,
                "requester": _thread_requester(slot, threads_per_core),
                "partid": partid,
                "pmg": pmg,
                "request_qos": request_qos,
                "workload_type": workload_type,
                "address_pattern": address_pattern,
                "operation_mix": operation_mix,
                "dependency_mode": dependency_mode,
                "independent_chains": independent_chains,
                "arrival_mode": arrival_mode,
                "issue_selection": issue_selection,
                "source_queue_depth": source_queue_depth,
                "eligible_scan_depth": eligible_scan_depth,
                "rate_value": rate_value,
                "rate_unit": rate_unit,
                "request_size_bytes": request_size,
                "read_ratio": read_ratio,
                "working_set_mb": working_set_mb,
                "address_base_mb": address_base_mb,
                "target_p99_ns": target_p99,
            }
        )
    if seen != set(range(expected_slots)):
        raise ParameterError(
            "Stimulus slots must cover every value "
            f"0..{expected_slots - 1}"
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
            "request_qos": row["request_qos"],
            "request_size_bytes": row["request_size_bytes"],
            "injection_scope": "per_requester",
            "read_ratio": row["read_ratio"],
            "address_pattern": row["address_pattern"],
            "operation_mix": row["operation_mix"],
            "dependency_mode": row["dependency_mode"],
            "independent_chains": row["independent_chains"],
            "arrival_mode": row["arrival_mode"],
            "issue_selection": row["issue_selection"],
            "source_queue_depth": row["source_queue_depth"],
            "eligible_scan_depth": row["eligible_scan_depth"],
            "working_set_bytes": (
                row["working_set_mb"] * 1024 * 1024
            ),
            "address_base_bytes": (
                row["address_base_mb"] * 1024 * 1024
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
        values, "duration_ns", DEFAULT_DURATION_NS, MIN_DURATION_NS, 5_000_000
    )
    control_interval_ns = _integer(
        values,
        "control_interval_ns",
        DEFAULT_CONTROL_INTERVAL_NS,
        MIN_CONTROL_INTERVAL_NS,
        duration_ns,
    )
    seed = _integer(
        values, "seed", 1234, 0, 2_147_483_647
    )
    active_cores = _integer(
        values, "active_cores", 8, 1, 16
    )
    threads_per_core = _integer(
        values, "threads_per_core", 2, 1, 4
    )
    l3_instances = min(
        _integer(
            values,
            "l3_instances",
            2,
            1,
            8,
        ),
        min(active_cores, 8),
    )
    l3_sets = _integer(
        values, "l3_sets", DEFAULT_L3_SETS, 8, 262_144
    )
    l3_ways = _integer(
        values, "l3_ways", DEFAULT_L3_WAYS, 1, 32
    )
    l3_line_size = _integer(
        values, "l3_line_size", 64, 16, 256
    )
    monitor_group_sets = _integer(
        values, "l3_monitor_group_sets", 8, 8, 8
    )
    l3_sampling_mode = _choice(
        values,
        "l3_sampling_mode",
        "fixed_first",
        ["fixed_first", "rotating"],
    )
    l3_sampling_rotation_period_monitor_cycles = _integer(
        values,
        "l3_sampling_rotation_period_monitor_cycles",
        1,
        1,
        1_000_000,
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
        values.get("l3_merge_same_line_misses", False)
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
    l3_history_weight = _number(
        values, "l3_history_weight", 0.75, 0, 1
    )
    l3_current_weight = _number(
        values, "l3_current_weight", 0.25, 0, 1
    )
    if abs(l3_history_weight + l3_current_weight - 1.0) > 1e-9:
        raise ParameterError(
            "L3 history_weight + current_weight must equal 1"
        )
    l3_qos_scheduler_enable = _boolean(
        values,
        "l3_qos_scheduler_enable",
        False,
    )
    l3_cbusy_qos_demote_per_level = _integer(
        values,
        "l3_cbusy_qos_demote_per_level",
        1,
        0,
        7,
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
    mc_history_weight = _number(
        values, "mc_history_weight", 0.95, 0, 1
    )
    mc_current_weight = _number(
        values, "mc_current_weight", 0.05, 0, 1
    )
    if abs(mc_history_weight + mc_current_weight - 1.0) > 1e-9:
        raise ParameterError(
            "MC history_weight + current_weight must equal 1"
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
    mc_qos_adjust_mode = _choice(
        values,
        "mc_qos_adjust_mode",
        "fixed_step",
        ["fixed_step", "error_weighted"],
    )
    mc_bmin_qos_promote = _integer(
        values, "mc_bmin_qos_promote", 2, 0, 7
    )
    mc_softlimit_qos_demote = _integer(
        values, "mc_softlimit_qos_demote", 2, 0, 7
    )
    mc_bmin_error_weight = _number(
        values, "mc_bmin_error_weight", 4.0, 0, 100
    )
    mc_bmax_error_weight = _number(
        values, "mc_bmax_error_weight", 4.0, 0, 100
    )
    mc_qos_error_deadband_percent = _number(
        values, "mc_qos_error_deadband_percent", 5.0, 0, 100
    )
    mc_qos_error_max_delta = _integer(
        values, "mc_qos_error_max_delta", 2, 0, 7
    )
    mc_qos_error_quantization = _choice(
        values,
        "mc_qos_error_quantization",
        "threshold_lut",
        ["round", "ceil", "threshold_lut"],
    )
    mc_qos_combiner_order = _choice(
        values,
        "mc_qos_combiner_order",
        "adjust_after_request_combine",
        [
            "adjust_before_request_combine",
            "adjust_after_request_combine",
        ],
    )
    mc_qos_combine_op = _choice(
        values,
        "mc_qos_combine_op",
        "replace",
        ["replace", "max", "average"],
    )
    mc_qos_map_8_to_4_enable = _boolean(
        values,
        "mc_qos_map_8_to_4_enable",
        False,
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
    cpu_cbusy_response_enable = _boolean(
        values,
        "cpu_cbusy_response_enable",
        False,
    )
    l3_cbusy_response_enable = _boolean(
        values,
        "l3_cbusy_response_enable",
        False,
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
    values = _apply_resctrl_groups(
        values,
        l3_ways,
        total_mc_bandwidth,
        max_outstanding,
        l3_instances,
        mc_count,
        active_cores,
        threads_per_core,
    )
    partid_configs = _parse_partid_configs(
        values,
        l3_ways,
        total_mc_bandwidth,
        max_outstanding,
    )
    values["stimulus_configs"] = _normalize_stimulus_configs(
        values.get("stimulus_configs"),
        active_cores,
        threads_per_core,
    )
    stimulus_configs = _parse_stimulus_configs(
        values,
        active_cores,
        threads_per_core,
    )
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

    policy = str(values.get("policy", "static_mpam"))
    if policy == "closed_loop_qos":
        policy = "static_mpam"
    if policy not in {"no_control", "static_mpam"}:
        raise ParameterError(
            "policy must be no_control or static_mpam"
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
            "sampling_mode": l3_sampling_mode,
            "sampling_rotation_period_monitor_cycles": (
                l3_sampling_rotation_period_monitor_cycles
            ),
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
            "cbusy_response_enable": l3_cbusy_response_enable,
            "qos_scheduler_enable": l3_qos_scheduler_enable,
            "cbusy_qos_demote_per_level": (
                l3_cbusy_qos_demote_per_level
            ),
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
            "qos_adjust_mode": mc_qos_adjust_mode,
            "bmin_qos_promote": mc_bmin_qos_promote,
            "softlimit_qos_demote": mc_softlimit_qos_demote,
            "bmin_error_weight": mc_bmin_error_weight,
            "bmax_error_weight": mc_bmax_error_weight,
            "qos_error_deadband_percent": mc_qos_error_deadband_percent,
            "qos_error_max_delta": mc_qos_error_max_delta,
            "qos_error_quantization": mc_qos_error_quantization,
            "qos_combiner_order": mc_qos_combiner_order,
            "qos_combine_op": mc_qos_combine_op,
            "qos_map_8_to_4_enable": mc_qos_map_8_to_4_enable,
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
                    "cpbm": row["l3_cpbm_by_domain"].get(
                        index,
                        row["cpbm"],
                    ),
                    "cmin_enable": row["cmin_enable"],
                    "cmax_enable": row["cmax_enable"],
                    "cpbm_enable": row["cpbm_enable"],
                    "mc_qos": row["mc_qos"],
                    "mc_qos_enable": row["mc_qos_enable"],
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
                    "bmax": row["mc_bmax_by_domain"].get(
                        index,
                        row["bmax_gbps"],
                    ),
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
                "cbusy_response_enable": cpu_cbusy_response_enable,
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
        "software": {
            "resctrl": {
                "enabled": bool(values.get("resctrl_enabled", False)),
                "groups": copy.deepcopy(
                    values.get("resctrl_groups", [])
                ),
            }
        },
        "workloads": workloads,
        "policies": [
            {
                "name": policy,
                "params": {
                    "interval_ns": control_interval_ns,
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
