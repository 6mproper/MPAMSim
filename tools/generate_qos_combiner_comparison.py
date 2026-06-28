from __future__ import annotations

import copy
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.config.loader import load_config
from src.sim.simulation import Simulation
from src.web.config_builder import build_config, default_parameters


CONFIG_SCHEMA = "mpamsim.config.parameters"
CONFIG_VERSION = 1
OUTPUT_DIR = Path("outputs/qos_combiner_comparison")

ORDERS = (
    ("path1", "adjust_before_request_combine"),
    ("path2", "adjust_after_request_combine"),
)
OPS = ("replace", "max", "average")


def _disable_all_stimulus(parameters: Dict[str, Any]) -> None:
    for row in parameters["stimulus_configs"]:
        row["enabled"] = False
        row["target_p99_ns"] = 0.0


def _disable_all_partid_controls(parameters: Dict[str, Any]) -> None:
    for row in parameters["partid_configs"]:
        row.update(
            {
                "monitor_enable": True,
                "cpbm_enable": False,
                "cmin_enable": False,
                "cmax_enable": False,
                "bmin_enable": False,
                "bmax_enable": False,
                "bmin_gbps": 0.0,
                "bmax_gbps": 16.0,
                "limit_mode": "softlimit",
                "mc_qos_enable": False,
                "mc_qos": 0,
                "cbusy_enable": False,
            }
        )


def _base_parameters(op: str) -> Dict[str, Any]:
    parameters = copy.deepcopy(default_parameters())
    background_qos = {
        "replace": 3,
        "max": 5,
        "average": 3,
    }[op]
    parameters.update(
        {
            "duration_ns": 5_000,
            "control_interval_ns": 128,
            "seed": 20260628,
            "active_cores": 2,
            "threads_per_core": 1,
            "l3_instances": 1,
            "memory_controllers": 1,
            "channels_per_mc": 1,
            "channel_bandwidth_gbps": 16,
            "mc_base_latency_ns": 80,
            "mc_queue_depth": 32,
            "mc_monitor_period_cycles": 128,
            "mc_history_weight": 0.0,
            "mc_current_weight": 1.0,
            "mc_bandwidth_hysteresis": 0.0,
            "mc_aging_mode": "none",
            "mc_qos_adjust_mode": "fixed_step",
            "mc_bmin_qos_promote": 0,
            "mc_softlimit_qos_demote": 3,
            "mc_qos_map_8_to_4_enable": False,
            "cpu_cbusy_response_enable": False,
            "l3_cbusy_response_enable": False,
            "policy": "static_mpam",
        }
    )
    _disable_all_stimulus(parameters)
    _disable_all_partid_controls(parameters)

    parameters["stimulus_configs"][0].update(
        {
            "enabled": True,
            "partid": 0,
            "pmg": 0,
            "request_qos": 7,
            "workload_type": "random_read",
            "address_pattern": "uniform_random",
            "dependency_mode": "independent",
            "issue_selection": "eligible_scan",
            "source_queue_depth": 8,
            "eligible_scan_depth": 8,
            "rate_value": 64.0,
            "rate_unit": "gbps",
            "request_size_bytes": 64,
            "read_ratio": 1.0,
            "working_set_mb": 4096,
            "address_base_mb": 0,
        }
    )
    parameters["stimulus_configs"][1].update(
        {
            "enabled": True,
            "partid": 1,
            "pmg": 1,
            "request_qos": 0,
            "workload_type": "random_read",
            "address_pattern": "uniform_random",
            "dependency_mode": "independent",
            "issue_selection": "eligible_scan",
            "source_queue_depth": 8,
            "eligible_scan_depth": 8,
            "rate_value": 64.0,
            "rate_unit": "gbps",
            "request_size_bytes": 64,
            "read_ratio": 1.0,
            "working_set_mb": 4096,
            "address_base_mb": 8192,
        }
    )
    parameters["partid_configs"][0].update(
        {
            "name": "qos_over_bmax",
            "bmax_enable": True,
            "bmax_gbps": 4.0,
            "limit_mode": "softlimit",
            "mc_qos_enable": True,
            "mc_qos": 4,
        }
    )
    parameters["partid_configs"][1].update(
        {
            "name": "qos_background",
            "mc_qos_enable": True,
            "mc_qos": background_qos,
        }
    )
    return parameters


def _reference_raw_qos(order: str, op: str) -> int:
    request_qos = 7
    config_qos = 4
    adjust_qos = -3

    def clamp(value: int) -> int:
        return max(0, min(7, int(value)))

    def combine(left: int, right: int) -> int:
        left = clamp(left)
        right = clamp(right)
        if op == "replace":
            return left
        if op == "max":
            return max(left, right)
        if op == "average":
            return (left + right) // 2
        raise ValueError(op)

    if order == "adjust_before_request_combine":
        return combine(clamp(config_qos + adjust_qos), request_qos)
    return clamp(combine(config_qos, request_qos) + adjust_qos)


def _run_case(case_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    raw = build_config(parameters, str(OUTPUT_DIR / "runs" / case_id))
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / f"{case_id}.yaml"
        config_path.write_text(
            yaml.safe_dump(raw, sort_keys=False),
            encoding="utf-8",
        )
        result = Simulation.from_config(load_config(config_path)).run()

    rows = [
        row
        for row in result.collector.msc_rows
        if row["msc_type"] == "memory_controller"
    ]
    partid0_rows = [
        row["per_partid"]["0"]
        for row in rows
        if row.get("per_partid", {}).get("0")
    ]
    cumulative = result.collector.cumulative_metrics(result.elapsed_ns)
    qos_rows = [
        row
        for row in partid0_rows
        if row.get("requests", 0) > 0
    ]
    controlled_rows = [
        row
        for row in qos_rows
        if row.get("softlimit_penalty_events", 0) > 0
    ]
    last = qos_rows[-1] if qos_rows else {}
    return {
        "case_id": case_id,
        "completed_requests": result.completed_requests,
        "reference_raw_qos": _reference_raw_qos(
            parameters["mc_qos_combiner_order"],
            parameters["mc_qos_combine_op"],
        ),
        "observed_raw_effective_qos_min": min(
            (row.get("raw_effective_qos_min", 0) for row in qos_rows),
            default=0,
        ),
        "observed_raw_effective_qos_max": max(
            (row.get("raw_effective_qos_max", 0) for row in qos_rows),
            default=0,
        ),
        "controlled_raw_effective_qos_min": min(
            (row.get("raw_effective_qos_min", 0) for row in controlled_rows),
            default=0,
        ),
        "controlled_raw_effective_qos_max": max(
            (row.get("raw_effective_qos_max", 0) for row in controlled_rows),
            default=0,
        ),
        "active_last_raw_effective_qos_avg": last.get(
            "raw_effective_qos_avg",
            0.0,
        ),
        "request_qos_last_avg": last.get("request_qos_avg", 0.0),
        "mpam_config_qos_last_avg": last.get("mpam_config_qos_avg", 0.0),
        "mpam_adjust_qos_last_avg": last.get("mpam_adjust_qos_avg", 0.0),
        "softlimit_events": sum(
            int(row.get("softlimit_penalty_events", 0))
            for row in partid0_rows
        ),
        "p0_total_bandwidth_gbps": cumulative.get(0, {}).get(
            "throughput_gbps",
            0.0,
        ),
        "p1_total_bandwidth_gbps": cumulative.get(1, {}).get(
            "throughput_gbps",
            0.0,
        ),
        "active_last_achieved_bandwidth_gbps": last.get(
            "achieved_bandwidth_gbps",
            0.0,
        ),
        "control_bandwidth_last_gbps": last.get(
            "control_bandwidth_gbps",
            0.0,
        ),
    }


def _write_markdown(rows: List[Dict[str, Any]], output: Path) -> None:
    lines = [
        "# MC QoS组合路径对比",
        "",
        "参考输入：`request_qos R=7`，`mpam_config_qos C=4`，`mpam_adjust_qos A=-3`。",
        "",
        "| case | 公式raw QoS | grant raw范围 | soft控制raw范围 | 最后活跃raw均值 | 最后活跃R/C/A均值 | soft事件 | P0/P1总带宽Gbps | 最后活跃带宽Gbps |",
        "| --- | ---: | --- | --- | ---: | --- | ---: | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {case_id} | {reference_raw_qos} | {observed_raw_effective_qos_min}..{observed_raw_effective_qos_max} | "
            "{controlled_raw_effective_qos_min}..{controlled_raw_effective_qos_max} | "
            "{active_last_raw_effective_qos_avg:.2f} | {request_qos_last_avg:.2f}/{mpam_config_qos_last_avg:.2f}/{mpam_adjust_qos_last_avg:.2f} | "
            "{softlimit_events} | {p0_total_bandwidth_gbps:.3f}/{p1_total_bandwidth_gbps:.3f} | "
            "{active_last_achieved_bandwidth_gbps:.3f} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "验证读法：",
            "- `公式raw QoS` 是同一组R=7、C=4、A=-3下的确定性公式检查，应作为组合逻辑是否正确的主判据。",
            "- `P0/P1总带宽` 来自可导入配置跑出的端到端结果，用于观察公式差异是否在竞争下改变服务份额。",
            "- `soft控制raw范围` 只统计P0在soft BMAX降档已生效时仍拿到grant的窗口；`0..0`表示该run里P0在soft状态下没有再拿到grant，通常说明背景PARTID赢得仲裁。",
            "- `replace`：两条路径在该参考输入下等价，都是1。",
            "- `max`：路径1可能让高request_qos覆盖soft BMAX降档；路径2把MC adjust放在最后，降档仍可见。",
            "- `average`：路径2同样把MC adjust作为最后控制动作，因此raw QoS比路径1更低。",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    rows: List[Dict[str, Any]] = []
    for order_label, order in ORDERS:
        for op in OPS:
            case_id = f"qos_combiner_{order_label}_{op}"
            parameters = _base_parameters(op)
            parameters["mc_qos_combiner_order"] = order
            parameters["mc_qos_combine_op"] = op
            payload = {
                "schema": CONFIG_SCHEMA,
                "version": CONFIG_VERSION,
                "exported_at": timestamp,
                "parameters": parameters,
            }
            (OUTPUT_DIR / f"{case_id}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            rows.append(_run_case(case_id, parameters))

    (OUTPUT_DIR / "comparison_summary.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(rows, OUTPUT_DIR / "comparison_summary.md")


if __name__ == "__main__":
    main()
