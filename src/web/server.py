from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import tempfile
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import unquote, urlparse

import yaml

from src.config.loader import load_config
from src.sim.simulation import Simulation

from .config_builder import ParameterError, build_config, default_parameters
from .config_metadata import config_metadata_payload


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = Path(__file__).resolve().parent / "static"
RUN_ROOT = PROJECT_ROOT / "outputs" / "web_runs"


@dataclass
class Job:
    id: str
    parameters: Dict[str, object]
    status: str = "queued"
    progress: float = 0.0
    message: str = "Waiting"
    error: Optional[str] = None
    result: Optional[Dict[str, object]] = None
    partial: Dict[str, object] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def snapshot(self) -> Dict[str, object]:
        with self.lock:
            payload = {
                "id": self.id,
                "status": self.status,
                "progress": self.progress,
                "message": self.message,
                "error": self.error,
                "partial": self.partial,
            }
            if self.result is not None:
                payload["result"] = self.result
            return payload


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, parameters: Dict[str, object]) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], parameters=parameters)
        with self._lock:
            self._jobs[job.id] = job
        thread = threading.Thread(target=self._run, args=(job,), daemon=True)
        thread.start()
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self, job: Job) -> None:
        run_dir = RUN_ROOT / job.id
        try:
            with job.lock:
                job.status = "validating"
                job.progress = 0.03
                job.message = "Validating configuration"
            raw = build_config(job.parameters, str(run_dir))
            RUN_ROOT.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".yaml",
                prefix=f"soc-flow-{job.id}-",
                delete=False,
                encoding="utf-8",
            ) as handle:
                yaml.safe_dump(raw, handle, sort_keys=False)
                config_path = Path(handle.name)
            try:
                config = load_config(config_path)
            finally:
                config_path.unlink(missing_ok=True)

            with job.lock:
                job.status = "running"
                job.progress = 0.08
                job.message = "Simulating request flow"

            simulation = Simulation.from_config(config)

            def on_progress(fraction, collector) -> None:
                with job.lock:
                    job.progress = min(0.9, 0.08 + fraction * 0.82)
                    job.message = "Simulating {:.0f}%".format(fraction * 100)
                    job.partial = {
                        "time_ns": collector.last_capture_ns,
                        "metrics": list(collector.metrics_rows),
                        "cpu": list(collector.requester_rows),
                        "cpu_mc": list(collector.requester_mc_rows),
                        "msc": _compact_msc_rows(collector.msc_rows),
                        "controls": list(collector.control_rows),
                    }

            result = simulation.run(progress_callback=on_progress)
            with job.lock:
                job.status = "exporting"
                job.progress = 0.94
                job.message = "Preparing result package"
            result.export(str(run_dir))

            cumulative = result.collector.cumulative_metrics(result.elapsed_ns)
            total_bytes = sum(int(row["bytes"]) for row in cumulative.values())
            result_payload = {
                "summary": {
                    "simulation_time_ns": result.elapsed_ns,
                    "total_throughput_gbps": total_bytes
                    * 8.0
                    / max(result.elapsed_ns, 1e-9),
                    "max_p99_latency_ns": max(
                        (
                            float(row["p99_latency_ns"])
                            for row in cumulative.values()
                        ),
                        default=0.0,
                    ),
                    "issued_requests": result.issued_requests,
                    "completed_requests": result.completed_requests,
                    "completion_ratio": result.completed_requests
                    / max(1, result.issued_requests),
                    "events_executed": result.events_executed,
                },
                "per_partid": {
                    str(partid): metrics
                    for partid, metrics in cumulative.items()
                },
                "metrics": result.collector.metrics_rows,
                "cpu": result.collector.requester_rows,
                "cpu_mc": result.collector.requester_mc_rows,
                "msc": _compact_msc_rows(result.collector.msc_rows),
                "controls": result.collector.control_rows,
                "timeline": result.collector.timeline_rows[-3000:],
                "topology": result._topology(),
                "report_url": f"/runs/{job.id}/report.html",
                "resolved_config_url": f"/runs/{job.id}/resolved_config.json",
            }
            with job.lock:
                job.status = "completed"
                job.progress = 1.0
                job.message = "Simulation completed"
                job.result = result_payload
                job.partial = {
                    "time_ns": result.elapsed_ns,
                    "metrics": result.collector.metrics_rows,
                    "cpu": result.collector.requester_rows,
                    "cpu_mc": result.collector.requester_mc_rows,
                    "msc": _compact_msc_rows(result.collector.msc_rows),
                    "controls": result.collector.control_rows,
                }
        except (ParameterError, ValueError) as exc:
            with job.lock:
                job.status = "failed"
                job.error = str(exc)
                job.message = "Configuration rejected"
        except Exception as exc:  # pragma: no cover - surfaced to the UI
            traceback.print_exc()
            with job.lock:
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}"
                job.message = "Simulation failed"


def _compact_msc_rows(rows):
    return [
        {
            key: value
            for key, value in row.items()
            if key != "requesters"
        }
        for row in rows
    ]


EXPERIMENT_CASES = (
    ("reference", "参考：BMAX/CBusy关闭", False, False),
    ("bmax_only", "仅 BMAX", True, False),
    ("cbusy_only", "仅 CBusy", False, True),
    ("combined", "BMAX + CBusy", True, True),
)


def derive_experiment_cases(
    parameters: Dict[str, object],
) -> Dict[str, Dict[str, object]]:
    active_partids = {
        int(row.get("partid", 0))
        for row in parameters.get("stimulus_configs", [])
        if isinstance(row, dict) and bool(row.get("enabled", True))
    }
    cases: Dict[str, Dict[str, object]] = {}
    for case_id, _, bmax_enabled, cbusy_enabled in EXPERIMENT_CASES:
        case = copy.deepcopy(parameters)
        case["policy"] = "static_mpam"
        for row in case.get("partid_configs", []):
            if not isinstance(row, dict):
                continue
            partid = int(row.get("partid", -1))
            row.update(
                {
                    "cpbm_enable": False,
                    "cmin_enable": False,
                    "cmax_enable": False,
                    "bmin_enable": False,
                    "bmax_enable": (
                        bmax_enabled and partid in active_partids
                    ),
                    "mc_qos_enable": False,
                    "cbusy_enable": (
                        cbusy_enabled and partid in active_partids
                    ),
                }
            )
        cases[case_id] = case
    return cases


def summarize_experiment_result(result) -> Dict[str, object]:
    elapsed_ns = result.elapsed_ns
    cumulative = result.collector.cumulative_metrics(elapsed_ns)
    mc_rows = [
        row
        for row in result.collector.msc_rows
        if row.get("msc_type") == "memory_controller"
    ]
    queue_by_time: Dict[float, float] = {}
    for row in mc_rows:
        time_ns = float(row.get("time_ns", 0))
        queue_by_time[time_ns] = (
            queue_by_time.get(time_ns, 0.0)
            + float(row.get("queue_occupancy", 0))
        )
    queue_area = 0.0
    previous_time = 0.0
    for time_ns, queue in sorted(queue_by_time.items()):
        queue_area += queue * max(0.0, time_ns - previous_time)
        previous_time = time_ns

    final_cpu: Dict[tuple, Dict[str, object]] = {}
    for row in result.collector.requester_rows:
        final_cpu[(row["requester_id"], int(row["partid"]))] = row

    per_partid: Dict[str, Dict[str, object]] = {}
    all_partids = set(cumulative)
    all_partids.update(int(row["partid"]) for row in final_cpu.values())
    for partid in sorted(all_partids):
        metrics = cumulative.get(partid, {})
        cpu_history = [
            row
            for row in result.collector.requester_rows
            if int(row["partid"]) == partid
        ]
        cpu_final = [
            row
            for (_, row_partid), row in final_cpu.items()
            if row_partid == partid
        ]
        queue_peak = 0.0
        throttle_ns = 0.0
        hard_blocks = 0
        for row in mc_rows:
            values = row.get("per_partid", {}).get(str(partid), {})
            queue_peak = max(
                queue_peak,
                float(values.get("cbusy_peak_queue_ratio", 0)),
            )
            throttle_ns += float(values.get("throttle_delay_ns", 0))
            hard_blocks += int(values.get("hardlimit_block_events", 0))
        per_partid[str(partid)] = {
            "throughput_gbps": float(metrics.get("throughput_gbps", 0)),
            "p99_latency_ns": float(metrics.get("p99_latency_ns", 0)),
            "requests": int(metrics.get("requests", 0)),
            "queue_ratio_peak": queue_peak,
            "throttle_delay_ns": throttle_ns,
            "hard_blocks": hard_blocks,
            "cbusy_stall_ns": sum(
                float(row.get("cbusy_stall_ns", 0))
                for row in cpu_final
            ),
            "configured_ostd_stall_ns": sum(
                float(row.get("configured_ostd_stall_ns", 0))
                for row in cpu_final
            ),
            "cbusy_transitions": sum(
                int(row.get("cbusy_transitions", 0))
                for row in cpu_final
            ),
            "effective_ostd_min": min(
                (
                    int(row.get("effective_max_outstanding", 0))
                    for row in cpu_history
                ),
                default=0,
            ),
        }

    total_bytes = sum(int(row.get("bytes", 0)) for row in cumulative.values())
    return {
        "simulation_time_ns": elapsed_ns,
        "total_throughput_gbps": total_bytes * 8.0 / max(elapsed_ns, 1e-9),
        "max_p99_latency_ns": max(
            (float(row.get("p99_latency_ns", 0)) for row in cumulative.values()),
            default=0.0,
        ),
        "completion_ratio": result.completed_requests
        / max(1, result.issued_requests),
        "mc_queue_peak": max(queue_by_time.values(), default=0.0),
        "mc_queue_area_entry_ns": queue_area,
        "throttle_delay_ns": sum(
            float(values.get("throttle_delay_ns", 0))
            for row in mc_rows
            for values in row.get("per_partid", {}).values()
        ),
        "hard_blocks": sum(
            int(values.get("hardlimit_block_events", 0))
            for row in mc_rows
            for values in row.get("per_partid", {}).values()
        ),
        "cbusy_stall_ns": sum(
            float(row.get("cbusy_stall_ns", 0))
            for row in final_cpu.values()
        ),
        "configured_ostd_stall_ns": sum(
            float(row.get("configured_ostd_stall_ns", 0))
            for row in final_cpu.values()
        ),
        "cbusy_transitions": sum(
            int(row.get("cbusy_transitions", 0))
            for row in final_cpu.values()
        ),
        "per_partid": per_partid,
    }


CONTROL_VERIFICATION_CASES = (
    ("cmin_off", "CMIN 关闭"),
    ("cmin_on", "CMIN = 50%"),
    ("cmax_full", "CMAX = 100%"),
    ("cmax_limited", "CMAX = 12.5%"),
    ("qos_equal", "MC QoS = 3 / 3"),
    ("qos_split", "MC QoS = 7 / 0"),
    ("bmin_off", "BMIN 关闭"),
    ("bmin_on", "BMIN = 24 Gbps"),
    ("bmax_solo_off", "BMAX 关闭 / 单流"),
    ("bmax_solo_soft", "BMAX soft / 单流"),
    ("bmax_solo_hard", "BMAX hard / 单流"),
    ("bmax_contended_off", "BMAX 关闭 / 竞争"),
    ("bmax_contended_soft", "BMAX soft / 竞争"),
)


def derive_control_verification_cases(
    parameters: Dict[str, object],
) -> Dict[str, Dict[str, object]]:
    def base_case() -> Dict[str, object]:
        case = copy.deepcopy(parameters)
        case.update(
            {
                "duration_ns": 120_000,
                "control_interval_ns": 20_000,
                "policy": "static_mpam",
                "l3_instances": 1,
                "l3_sets": 8,
                "l3_ways": 16,
                "memory_controllers": 1,
                "channels_per_mc": 1,
                "channel_bandwidth_gbps": 32,
                "max_outstanding": 64,
                "core_max_outstanding": 128,
                "core_ostd_policy": "shared",
                "noc_flit_bytes": 64,
                "noc_link_slots_per_direction": 64,
            }
        )
        for row in case.get("stimulus_configs", []):
            row["enabled"] = False
        for row in case.get("partid_configs", []):
            row.update(
                {
                    "cpbm_enable": False,
                    "cmin_enable": False,
                    "cmax_enable": False,
                    "cpbm": "ffff",
                    "cmin": 0,
                    "cmax": 100,
                    "bmin_enable": False,
                    "bmax_enable": False,
                    "mc_qos_enable": False,
                    "cbusy_enable": False,
                    "bmin_gbps": 0,
                    "bmax_gbps": 10,
                    "limit_mode": "softlimit",
                    "mc_qos": 0,
                }
            )
        return case

    def stimulus(
        case: Dict[str, object],
        slot: int,
        partid: int,
        rate_gbps: float,
        workload_type: str = "stream",
    ) -> None:
        row = case["stimulus_configs"][slot]
        row.update(
            {
                "enabled": True,
                "partid": partid,
                "pmg": partid,
                "workload_type": workload_type,
                "rate_value": rate_gbps,
                "rate_unit": "gbps",
                "request_size_bytes": 64,
                "read_ratio": 1.0,
                "working_set_mb": 64,
                "target_p99_ns": 0,
            }
        )

    cases: Dict[str, Dict[str, object]] = {}
    for case_id, _ in CONTROL_VERIFICATION_CASES:
        case = base_case()
        p0 = case["partid_configs"][0]
        if case_id.startswith("cmin"):
            stimulus(case, 0, 0, 20, "random_read")
            stimulus(case, 1, 1, 80, "random_read")
            p0.update(
                {
                    "cpbm_enable": True,
                    "cmin_enable": case_id == "cmin_on",
                    "cmin": 50,
                    "cmax": 100,
                }
            )
            case["partid_configs"][1]["cpbm_enable"] = True
        elif case_id.startswith("cmax"):
            stimulus(case, 0, 0, 80, "random_read")
            p0.update(
                {
                    "cpbm_enable": True,
                    "cmax_enable": True,
                    "cmax": 12.5 if case_id == "cmax_limited" else 100,
                }
            )
        elif case_id.startswith("qos"):
            stimulus(case, 0, 0, 64)
            stimulus(case, 1, 1, 64)
            for partid in (0, 1):
                case["partid_configs"][partid].update(
                    {
                        "cpbm_enable": True,
                        "cmax_enable": True,
                        "cpbm": "0000",
                        "cmax": 0,
                        "mc_qos_enable": True,
                        "mc_qos": (
                            7
                            if case_id == "qos_split" and partid == 0
                            else 0
                            if case_id == "qos_split"
                            else 3
                        ),
                    }
                )
        elif case_id.startswith("bmin"):
            stimulus(case, 0, 0, 64)
            stimulus(case, 1, 1, 64)
            for partid in (0, 1):
                case["partid_configs"][partid].update(
                    {
                        "cpbm_enable": True,
                        "cmax_enable": True,
                        "cpbm": "0000",
                        "cmax": 0,
                    }
                )
            p0.update(
                {
                    "bmin_enable": case_id == "bmin_on",
                    "bmin_gbps": 24,
                    "bmax_gbps": 32,
                }
            )
        elif case_id.startswith("bmax_solo"):
            stimulus(case, 0, 0, 64)
            p0.update(
                {
                    "cpbm_enable": True,
                    "cmax_enable": True,
                    "cpbm": "0000",
                    "cmax": 0,
                    "bmax_enable": case_id != "bmax_solo_off",
                    "limit_mode": (
                        "hardlimit"
                        if case_id == "bmax_solo_hard"
                        else "softlimit"
                    ),
                }
            )
        else:
            stimulus(case, 0, 0, 64)
            stimulus(case, 1, 1, 64)
            for partid in (0, 1):
                case["partid_configs"][partid].update(
                    {
                        "cpbm_enable": True,
                        "cmax_enable": True,
                        "cpbm": "0000",
                        "cmax": 0,
                    }
                )
            p0.update(
                {
                    "bmax_enable": case_id == "bmax_contended_soft",
                    "limit_mode": "softlimit",
                }
            )
        cases[case_id] = case
    return cases


def summarize_control_verification_case(result) -> Dict[str, object]:
    cumulative = result.collector.cumulative_metrics(result.elapsed_ns)
    cache_rows = [
        row
        for row in result.collector.msc_rows
        if row.get("msc_type") == "cache"
    ]
    mc_rows = [
        row
        for row in result.collector.msc_rows
        if row.get("msc_type") == "memory_controller"
    ]
    partids = sorted(
        set(cumulative)
        | {
            int(partid)
            for row in cache_rows + mc_rows
            for partid in row.get("per_partid", {})
        }
    )
    per_partid = {}
    for partid in partids:
        key = str(partid)
        latest_cache = next(
            (
                row.get("per_partid", {}).get(key, {})
                for row in reversed(cache_rows)
                if key in row.get("per_partid", {})
            ),
            {},
        )
        per_partid[key] = {
            "throughput_gbps": float(
                cumulative.get(partid, {}).get("throughput_gbps", 0)
            ),
            "p99_latency_ns": float(
                cumulative.get(partid, {}).get("p99_latency_ns", 0)
            ),
            "sampled_way_count": int(
                latest_cache.get("sampled_way_count", 0)
            ),
            "cmin_protected_candidates": sum(
                int(
                    row.get("per_partid", {})
                    .get(key, {})
                    .get("cmin_protected_evictions", 0)
                )
                for row in cache_rows
            ),
            "allocation_denials": sum(
                int(
                    row.get("per_partid", {})
                    .get(key, {})
                    .get("allocation_denials", 0)
                )
                for row in cache_rows
            ),
            "bmin_priority_requests": sum(
                int(
                    row.get("per_partid", {})
                    .get(key, {})
                    .get("bmin_priority_requests", 0)
                )
                for row in mc_rows
            ),
            "softlimit_requests": sum(
                int(
                    row.get("per_partid", {})
                    .get(key, {})
                    .get("softlimit_requests", 0)
                )
                for row in mc_rows
            ),
            "softlimit_penalty_events": sum(
                int(
                    row.get("per_partid", {})
                    .get(key, {})
                    .get("softlimit_penalty_events", 0)
                )
                for row in mc_rows
            ),
            "hardlimit_block_events": sum(
                int(
                    row.get("per_partid", {})
                    .get(key, {})
                    .get("hardlimit_block_events", 0)
                )
                for row in mc_rows
            ),
            "throttle_delay_ns": sum(
                float(
                    row.get("per_partid", {})
                    .get(key, {})
                    .get("throttle_delay_ns", 0)
                )
                for row in mc_rows
            ),
            "base_qos": max(
                (
                    float(
                        row.get("per_partid", {})
                        .get(key, {})
                        .get("base_qos", 0)
                    )
                    for row in mc_rows
                ),
                default=0.0,
            ),
            "effective_qos_avg": (
                sum(
                    float(
                        row.get("per_partid", {})
                        .get(key, {})
                        .get("effective_qos_avg", 0)
                    )
                    * float(
                        row.get("per_partid", {})
                        .get(key, {})
                        .get("requests", 0)
                    )
                    for row in mc_rows
                )
                / max(
                    1.0,
                    sum(
                        float(
                            row.get("per_partid", {})
                            .get(key, {})
                            .get("requests", 0)
                        )
                        for row in mc_rows
                    ),
                )
            ),
        }
    return {
        "simulation_time_ns": result.elapsed_ns,
        "l3_queue_peak": max(
            (float(row.get("queue_peak", 0)) for row in cache_rows),
            default=0.0,
        ),
        "per_partid": per_partid,
    }


def evaluate_control_verification(
    results: Dict[str, Dict[str, object]],
) -> list:
    def p(case_id: str, field: str) -> float:
        return float(
            results[case_id]["per_partid"]["0"].get(field, 0)
        )

    checks = []

    def add(
        check_id: str,
        label: str,
        passed: bool,
        expected: str,
        evidence: str,
    ) -> None:
        checks.append(
            {
                "id": check_id,
                "label": label,
                "passed": bool(passed),
                "expected": expected,
                "evidence": evidence,
            }
        )

    cmin_off = p("cmin_off", "sampled_way_count")
    cmin_on = p("cmin_on", "sampled_way_count")
    cmin_protected = p("cmin_on", "cmin_protected_candidates")
    add(
        "cmin",
        "CMIN 替换保护",
        cmin_on >= 8 and cmin_on > cmin_off and cmin_protected > 0,
        "CMIN=8 时至少保留 8 个 sampled ways，并跳过受保护 victim",
        f"关闭={cmin_off:.0f} ways，启用={cmin_on:.0f} ways，保护跳过={cmin_protected:.0f}",
    )

    cmax_full = p("cmax_full", "sampled_way_count")
    cmax_limited = p("cmax_limited", "sampled_way_count")
    add(
        "cmax",
        "CMAX 分配上界",
        cmax_limited <= 2 and cmax_full > cmax_limited,
        "CMAX=12.5% 时全局 sampled ownership 不超过 2/16 lines",
        f"全量={cmax_full:.0f} ways，限制={cmax_limited:.0f} ways",
    )

    qos_equal = p("qos_equal", "throughput_gbps")
    qos_split = p("qos_split", "throughput_gbps")
    qos_effective = p("qos_split", "effective_qos_avg")
    add(
        "mc_qos",
        "MC 3-bit QoS 仲裁",
        qos_effective >= 6.0 and qos_split > qos_equal * 1.05,
        "相同需求下，QoS 7 相比对等 QoS 获得更高仲裁份额",
        f"对等={qos_equal:.2f} Gbps，7/0={qos_split:.2f} Gbps，effective={qos_effective:.2f}",
    )

    bmin_off = p("bmin_off", "throughput_gbps")
    bmin_on = p("bmin_on", "throughput_gbps")
    bmin_requests = p("bmin_on", "bmin_priority_requests")
    add(
        "bmin",
        "BMIN 调度偏好",
        bmin_requests > 0 and bmin_on > bmin_off * 1.05,
        "BMIN credit 产生优先请求并提高受保护 PARTID 吞吐",
        f"关闭={bmin_off:.2f} Gbps，启用={bmin_on:.2f} Gbps，优先请求={bmin_requests:.0f}",
    )

    solo_off = p("bmax_solo_off", "throughput_gbps")
    solo_soft = p("bmax_solo_soft", "throughput_gbps")
    solo_hard = p("bmax_solo_hard", "throughput_gbps")
    soft_requests = p("bmax_solo_soft", "softlimit_requests")
    add(
        "bmax_soft_uncontended",
        "BMAX soft 无竞争借用",
        soft_requests > 0 and solo_soft >= solo_off * 0.85,
        "无竞争时 softlimit 吞吐接近关闭 BMAX，保持 work-conserving",
        f"关闭={solo_off:.2f} Gbps，soft={solo_soft:.2f} Gbps，超限选中={soft_requests:.0f}",
    )

    hard_blocks = p("bmax_solo_hard", "hardlimit_block_events")
    hard_throttle = p("bmax_solo_hard", "throttle_delay_ns")
    add(
        "bmax_hard",
        "BMAX hard token 阻塞",
        hard_blocks > 0 and hard_throttle > 0 and solo_hard <= 12.5,
        "10 Gbps hardlimit 阻塞 dispatch，并使吞吐接近配置上限",
        f"吞吐={solo_hard:.2f} Gbps，阻塞={hard_blocks:.0f}，throttle={hard_throttle:.1f} ns",
    )

    contended_off = p("bmax_contended_off", "throughput_gbps")
    contended_soft = p("bmax_contended_soft", "throughput_gbps")
    contended_events = p(
        "bmax_contended_soft",
        "softlimit_penalty_events",
    )
    add(
        "bmax_soft_contended",
        "BMAX soft 竞争降权",
        contended_events > 0 and contended_soft < contended_off * 0.95,
        "存在竞争时，超限 soft 流量失去调度偏好",
        f"关闭={contended_off:.2f} Gbps，soft={contended_soft:.2f} Gbps，降权事件={contended_events:.0f}",
    )
    return checks


class ExperimentManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, parameters: Dict[str, object]) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], parameters=parameters)
        with self._lock:
            self._jobs[job.id] = job
        threading.Thread(
            target=self._run,
            args=(job,),
            daemon=True,
        ).start()
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self, job: Job) -> None:
        experiment_dir = RUN_ROOT / f"experiment-{job.id}"
        try:
            cases = derive_experiment_cases(job.parameters)
            completed = []
            results = {}
            for index, (case_id, label, _, _) in enumerate(EXPERIMENT_CASES):
                with job.lock:
                    job.status = "running"
                    job.progress = index / len(EXPERIMENT_CASES)
                    job.message = f"Running {label}"
                    job.partial = {
                        "completed_cases": list(completed),
                        "results": dict(results),
                    }
                case_dir = experiment_dir / case_id
                raw = build_config(cases[case_id], str(case_dir))
                RUN_ROOT.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".yaml",
                    prefix=f"soc-flow-exp-{job.id}-{case_id}-",
                    delete=False,
                    encoding="utf-8",
                ) as handle:
                    yaml.safe_dump(raw, handle, sort_keys=False)
                    config_path = Path(handle.name)
                try:
                    simulation = Simulation.from_config(
                        load_config(config_path)
                    )
                finally:
                    config_path.unlink(missing_ok=True)
                result = simulation.run()
                result.export(str(case_dir))
                summary = summarize_experiment_result(result)
                summary["id"] = case_id
                summary["label"] = label
                summary["report_url"] = (
                    f"/runs/experiment-{job.id}/{case_id}/report.html"
                )
                results[case_id] = summary
                completed.append(case_id)

            payload = {
                "cases": [
                    results[case_id]
                    for case_id, _, _, _ in EXPERIMENT_CASES
                ],
                "seed": int(job.parameters.get("seed", 0)),
            }
            experiment_dir.mkdir(parents=True, exist_ok=True)
            (experiment_dir / "experiment_summary.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            with job.lock:
                job.status = "completed"
                job.progress = 1.0
                job.message = "Mechanism comparison completed"
                job.result = payload
                job.partial = {
                    "completed_cases": list(completed),
                    "results": dict(results),
                }
        except (ParameterError, ValueError) as exc:
            with job.lock:
                job.status = "failed"
                job.error = str(exc)
                job.message = "Experiment configuration rejected"
        except Exception as exc:  # pragma: no cover
            traceback.print_exc()
            with job.lock:
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}"
                job.message = "Experiment failed"


JOBS = JobManager()
EXPERIMENTS = ExperimentManager()


class ControlVerificationManager(ExperimentManager):
    def _run(self, job: Job) -> None:
        verification_dir = RUN_ROOT / f"verification-{job.id}"
        try:
            cases = derive_control_verification_cases(job.parameters)
            completed = []
            results = {}
            for index, (case_id, label) in enumerate(
                CONTROL_VERIFICATION_CASES
            ):
                with job.lock:
                    job.status = "running"
                    job.progress = index / len(CONTROL_VERIFICATION_CASES)
                    job.message = f"Verifying {label}"
                    job.partial = {
                        "completed_cases": list(completed),
                        "results": dict(results),
                    }
                case_dir = verification_dir / case_id
                raw = build_config(cases[case_id], str(case_dir))
                if case_id.startswith("cmin_"):
                    raw["workloads"][1]["start_ns"] = 40_000
                RUN_ROOT.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".yaml",
                    prefix=f"soc-flow-verify-{job.id}-{case_id}-",
                    delete=False,
                    encoding="utf-8",
                ) as handle:
                    yaml.safe_dump(raw, handle, sort_keys=False)
                    config_path = Path(handle.name)
                try:
                    result = Simulation.from_config(
                        load_config(config_path)
                    ).run()
                finally:
                    config_path.unlink(missing_ok=True)
                result.export(str(case_dir))
                summary = summarize_control_verification_case(result)
                summary.update(
                    {
                        "id": case_id,
                        "label": label,
                        "report_url": (
                            f"/runs/verification-{job.id}/{case_id}/report.html"
                        ),
                    }
                )
                results[case_id] = summary
                completed.append(case_id)

            checks = evaluate_control_verification(results)
            payload = {
                "checks": checks,
                "passed": sum(int(row["passed"]) for row in checks),
                "total": len(checks),
                "algorithm_parameters": {
                    key: cases["cmin_off"].get(key)
                    for key in (
                        "l3_queue_depth",
                        "l3_lookup_parallelism",
                        "mc_token_bucket_window_ns",
                        "mc_aging_ns",
                        "mc_qos_aging_max_steps",
                        "mc_bmin_qos_promote",
                        "mc_softlimit_qos_demote",
                    )
                },
                "cases": [
                    results[case_id]
                    for case_id, _ in CONTROL_VERIFICATION_CASES
                ],
                "seed": int(job.parameters.get("seed", 0)),
            }
            verification_dir.mkdir(parents=True, exist_ok=True)
            (verification_dir / "verification_summary.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            with job.lock:
                job.status = "completed"
                job.progress = 1.0
                job.message = "Control verification completed"
                job.result = payload
                job.partial = {
                    "completed_cases": list(completed),
                    "results": dict(results),
                }
        except (ParameterError, ValueError) as exc:
            with job.lock:
                job.status = "failed"
                job.error = str(exc)
                job.message = "Verification configuration rejected"
        except Exception as exc:  # pragma: no cover
            traceback.print_exc()
            with job.lock:
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}"
                job.message = "Control verification failed"


VERIFICATIONS = ControlVerificationManager()


class Handler(BaseHTTPRequestHandler):
    server_version = "SoCFlowConsole/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/defaults":
            self._json(
                {
                    "parameters": default_parameters(),
                    "ui_metadata": config_metadata_payload(),
                }
            )
            return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            job = JOBS.get(job_id)
            if job is None:
                self._json({"error": "Unknown job"}, HTTPStatus.NOT_FOUND)
                return
            self._json(job.snapshot())
            return
        if path.startswith("/api/experiments/"):
            job_id = path.rsplit("/", 1)[-1]
            job = EXPERIMENTS.get(job_id)
            if job is None:
                self._json(
                    {"error": "Unknown experiment"},
                    HTTPStatus.NOT_FOUND,
                )
                return
            self._json(job.snapshot())
            return
        if path.startswith("/api/verifications/"):
            job_id = path.rsplit("/", 1)[-1]
            job = VERIFICATIONS.get(job_id)
            if job is None:
                self._json(
                    {"error": "Unknown verification"},
                    HTTPStatus.NOT_FOUND,
                )
                return
            self._json(job.snapshot())
            return
        if path.startswith("/runs/"):
            relative = path[len("/runs/") :]
            self._serve_file(RUN_ROOT, relative)
            return
        if path == "/":
            self._serve_file(STATIC_ROOT, "index.html")
            return
        if path.startswith("/static/"):
            self._serve_file(STATIC_ROOT, path[len("/static/") :])
            return
        self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path not in {
            "/api/jobs",
            "/api/experiments",
            "/api/verifications",
        }:
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            parameters = payload.get("parameters", {})
            if not isinstance(parameters, dict):
                raise ValueError("parameters must be an object")
            if self.path == "/api/experiments":
                job = EXPERIMENTS.create(parameters)
            elif self.path == "/api/verifications":
                job = VERIFICATIONS.create(parameters)
            else:
                job = JOBS.create(parameters)
            self._json(
                {"job_id": job.id, "status": job.status},
                HTTPStatus.ACCEPTED,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _serve_file(self, root: Path, relative: str) -> None:
        root = root.resolve()
        target = (root / relative).resolve()
        if root not in target.parents and target != root:
            self._json({"error": "Invalid path"}, HTTPStatus.BAD_REQUEST)
            return
        if not target.is_file():
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(
        self,
        value: Dict[str, object],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        print("[web] " + fmt % args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local SoC flow console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"SoC Flow Console: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
