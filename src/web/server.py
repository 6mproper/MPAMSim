from __future__ import annotations

import argparse
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


JOBS = JobManager()


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
        if self.path != "/api/jobs":
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
