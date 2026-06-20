from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from src.cache.cache_msc import CacheMSC
from src.config.schema import ProjectConfig
from src.ddr.memctrl import MemoryControllerMSC
from src.monitor.collector import MetricsCollector
from src.monitor.exporter import write_csv, write_json
from src.monitor.report import render_report
from src.mpam.settings import SettingsTable
from src.noc.fabric import NocFabric
from src.scheduler.factory import build_policies
from src.traffic.generator import WorkloadGenerator
from src.traffic.request import Request
from src.traffic.requester import RequesterRuntime

from .kernel import SimulationKernel


@dataclass
class SimulationResult:
    config: ProjectConfig
    collector: MetricsCollector
    elapsed_ns: float
    issued_requests: int
    completed_requests: int
    events_executed: int

    def export(self, output_dir: Optional[str] = None) -> Path:
        directory = Path(output_dir or self.config.outputs.dir)
        directory.mkdir(parents=True, exist_ok=True)
        cumulative = self.collector.cumulative_metrics(self.elapsed_ns)
        total_bytes = sum(int(metrics["bytes"]) for metrics in cumulative.values())
        summary_metrics = {
            "total_throughput_gbps": total_bytes * 8.0 / max(self.elapsed_ns, 1e-9),
            "max_p99_latency_ns": max(
                (float(metrics["p99_latency_ns"]) for metrics in cumulative.values()),
                default=0.0,
            ),
            "issued_requests": self.issued_requests,
            "completed_requests": self.completed_requests,
            "completion_ratio": self.completed_requests / max(1, self.issued_requests),
            "events_executed": self.events_executed,
        }
        summary = {
            "scenario": self.config.source_path.stem,
            "seed": self.config.simulation.seed,
            "simulation_time_ns": self.elapsed_ns,
            "policies": [policy.name for policy in self.config.policies],
            "summary_metrics": summary_metrics,
            "per_partid": {str(partid): metrics for partid, metrics in cumulative.items()},
        }
        write_json(directory / "run_summary.json", summary)
        write_json(directory / "resolved_config.json", self.config.raw)
        write_json(directory / "topology.json", self._topology())
        write_csv(directory / "metrics.csv", self.collector.metrics_rows)
        write_csv(
            directory / "per_cpu_partid.csv",
            self.collector.requester_rows,
        )
        write_csv(
            directory / "per_partid_latency.csv",
            [{"partid": partid, **metrics} for partid, metrics in cumulative.items()],
        )
        write_csv(directory / "per_msc_utilization.csv", self.collector.msc_rows)
        write_csv(directory / "control_trace.csv", self.collector.control_rows)
        write_csv(directory / "timeline_trace.csv", self.collector.timeline_rows)
        if self.config.outputs.generate_report:
            render_report(directory)
        return directory

    def render_report(self, output_path: str) -> Path:
        output = Path(output_path)
        run_dir = output.parent
        report = render_report(run_dir)
        if report != output:
            output.write_text(report.read_text(encoding="utf-8"), encoding="utf-8")
        return output

    def _topology(self) -> Dict[str, object]:
        nodes: List[Dict[str, object]] = []
        links: List[Dict[str, str]] = []
        for cluster in self.config.clusters:
            nodes.append({"id": cluster.id, "type": "cluster"})
            for core in cluster.cores:
                nodes.append({"id": core, "type": "core", "parent": cluster.id})
                links.append({"source": cluster.id, "target": core})
        for requester in self.config.requesters:
            nodes.append(
                {
                    "id": requester.id,
                    "type": requester.type,
                    "parent": requester.core or "",
                    "attach_node": requester.attach_node,
                }
            )
            if requester.core:
                links.append({"source": requester.core, "target": requester.id})
            links.append({"source": requester.id, "target": requester.attach_node})
        for index in range(self.config.noc.routers):
            nodes.append({"id": f"r{index}", "type": "noc_router"})
        for cache in self.config.caches:
            nodes.append({"id": cache.id, "type": "cache"})
        for mc in self.config.memory_controllers:
            nodes.append({"id": mc.id, "type": "memory_controller"})
        for cluster in self.config.clusters:
            links.append({"source": cluster.id, "target": cluster.l3})
        for cache in self.config.caches:
            for mc in self.config.memory_controllers:
                links.append({"source": cache.id, "target": mc.id})
        return {"nodes": nodes, "links": links}


class Simulation:
    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.kernel = SimulationKernel()
        self.collector = MetricsCollector(config.outputs.trace_requests)
        configured_partids_by_requester: Dict[str, set] = {
            item.id: set()
            for item in config.requesters
        }
        for workload in config.workloads:
            for requester_id in workload.requesters:
                configured_partids_by_requester[requester_id].add(
                    workload.partid
                )
        self.requesters = {
            item.id: RequesterRuntime(
                item,
                tuple(
                    sorted(
                        configured_partids_by_requester[item.id]
                    )
                ),
            )
            for item in config.requesters
        }
        self._request_id = 0
        self._interval_index = 0
        self._delivered_cbusy_levels: Dict[
            tuple, int
        ] = {}
        self._progress_callback: Optional[
            Callable[[float, MetricsCollector], None]
        ] = None

        controls = config.controls_by_msc
        no_control = len(config.policies) == 1 and config.policies[0].name == "no_control"
        self.enforce_controls = not no_control
        self.settings_tables: Dict[str, SettingsTable] = {
            cache.id: SettingsTable(controls.get(cache.id, ()))
            for cache in config.caches
        }
        self.settings_tables.update(
            {
                mc.id: SettingsTable(controls.get(mc.id, ()))
                for mc in config.memory_controllers
            }
        )
        self.noc = NocFabric(self.kernel, config.noc)
        self.memory_controllers = {
            mc.id: MemoryControllerMSC(
                self.kernel,
                mc,
                self.settings_tables[mc.id],
                self._complete,
                on_cbusy=self._cbusy_feedback,
                enforce_controls=self.enforce_controls,
            )
            for mc in config.memory_controllers
        }
        self.caches = {
            cache.id: CacheMSC(
                self.kernel,
                cache,
                self.settings_tables[cache.id],
                config.simulation.seed + 100 + index,
                self._complete,
                self._cache_miss,
                enforce_controls=self.enforce_controls,
            )
            for index, cache in enumerate(config.caches)
        }
        self.components = [
            self.noc,
            *self.caches.values(),
            *self.memory_controllers.values(),
        ]
        targets = {
            workload.partid: workload.target_p99_ns
            for workload in config.workloads
            if workload.target_p99_ns is not None
        }
        mc_tables = {
            mc_id: self.settings_tables[mc_id]
            for mc_id in self.memory_controllers
        }
        self.policies = build_policies(config.policies, targets, mc_tables)
        self.generators = self._build_generators()

    @classmethod
    def from_config(cls, config: ProjectConfig) -> "Simulation":
        return cls(config)

    def _build_generators(self) -> List[WorkloadGenerator]:
        generators: List[WorkloadGenerator] = []
        seed_offset = 0
        for workload in self.config.workloads:
            for requester_id in workload.requesters:
                requester = self.requesters[requester_id]
                generators.append(
                    WorkloadGenerator(
                        kernel=self.kernel,
                        workload=workload,
                        requester=requester,
                        requester_count=len(workload.requesters),
                        seed=self.config.simulation.seed + 1000 + seed_offset,
                        next_request_id=self._next_request_id,
                        submit=self._submit,
                        default_priority=self._default_priority(workload.partid),
                    )
                )
                seed_offset += 1
        return generators

    def _default_priority(self, partid: int) -> int:
        # MC QoS is local to the memory controller in this model. NoC
        # arbitration remains neutral until a separate NoC QoS contract exists.
        return 0

    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _submit(self, request: Request) -> None:
        requester = self.config.requester_by_id[request.requester_id]
        cache_id = self.config.core_to_cache.get(requester.core or "", self.config.caches[0].id)
        request.cache_id = cache_id
        cache = self.caches[cache_id]
        self.noc.receive(request, cache.receive)

    def _cache_miss(self, request: Request) -> None:
        line_size = self.config.cache_by_id[request.cache_id].line_size
        index = (request.addr // max(1, line_size)) % len(self.config.memory_controllers)
        mc_id = self.config.memory_controllers[index].id
        self.memory_controllers[mc_id].receive(request)

    def _complete(self, request: Request) -> None:
        self.requesters[request.requester_id].on_completion(
            request.partid
        )
        self.collector.on_complete(request, self.kernel.now_ns)

    def _cbusy_feedback(
        self,
        msc_id: str,
        partid: int,
        level: int,
        cap: int,
    ) -> None:
        key = (msc_id, partid)
        old_level = self._delivered_cbusy_levels.get(key, 0)
        self._delivered_cbusy_levels[key] = level
        self.collector.record_control(
            self.kernel.now_ns,
            "mc_cbusy",
            msc_id,
            partid,
            "cbusy_level",
            old_level,
            level,
            f"effective OSTD cap {cap}",
        )
        for requester in self.requesters.values():
            if partid in requester.configured_partids:
                requester.set_cbusy(
                    msc_id,
                    partid,
                    level,
                    cap,
                )

    def _control_interval(self) -> None:
        self._interval_index += 1
        metrics = self.collector.capture_interval(
            self.kernel.now_ns,
            self.components,
            self.requesters.values(),
        )
        for policy in self.policies:
            updates = policy.on_interval(self._interval_index, self.kernel.now_ns, metrics)
            for update in updates:
                table = self.settings_tables.get(update.target_msc)
                if table is None:
                    continue
                old_value = table.update(update.partid, update.field, update.value)
                self.collector.record_control(
                    self.kernel.now_ns,
                    update.policy or policy.name,
                    update.target_msc,
                    update.partid,
                    update.field,
                    old_value,
                    update.value,
                    update.reason,
                )
        if self._progress_callback is not None:
            self._progress_callback(
                min(1.0, self.kernel.now_ns / max(1.0, self._run_until_ns)),
                self.collector,
            )
        next_time = self.kernel.now_ns + self.config.simulation.control_interval_ns
        if next_time <= self._run_until_ns:
            self.kernel.schedule_at(next_time, self._control_interval, "control-interval")

    def run(
        self,
        until_ns: Optional[float] = None,
        progress_callback: Optional[
            Callable[[float, MetricsCollector], None]
        ] = None,
    ) -> SimulationResult:
        self._run_until_ns = float(until_ns or self.config.simulation.time_ns)
        self._progress_callback = progress_callback
        for generator in self.generators:
            generator.start()
        first_interval = min(
            float(self.config.simulation.control_interval_ns),
            self._run_until_ns,
        )
        if first_interval > 0:
            self.kernel.schedule_at(first_interval, self._control_interval, "control-interval")
        self.kernel.run(self._run_until_ns)
        if self.collector.last_capture_ns < self._run_until_ns:
            self.collector.capture_interval(
                self._run_until_ns,
                self.components,
                self.requesters.values(),
            )
        if self._progress_callback is not None:
            self._progress_callback(1.0, self.collector)
        issued = sum(requester.issued for requester in self.requesters.values())
        return SimulationResult(
            config=self.config,
            collector=self.collector,
            elapsed_ns=self._run_until_ns,
            issued_requests=issued,
            completed_requests=self.collector.total_completed,
            events_executed=self.kernel.events_executed,
        )
