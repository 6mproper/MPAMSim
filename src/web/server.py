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
                    "priority_enable": False,
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


class Handler(BaseHTTPRequestHandler):
    server_version = "SoCFlowConsole/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/defaults":
            self._json({"parameters": default_parameters()})
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
        if self.path not in {"/api/jobs", "/api/experiments"}:
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
            job = (
                EXPERIMENTS.create(parameters)
                if self.path == "/api/experiments"
                else JOBS.create(parameters)
            )
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
