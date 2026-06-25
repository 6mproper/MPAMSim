from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from src.cache.cache_msc import CacheMSC
from src.config.schema import ProjectConfig
from src.contracts.capabilities import ComponentRegistry
from src.contracts.telemetry import (
    ControlEvent,
    MetricSemantic,
    MonitorSample,
)
from src.ddr.memctrl import MemoryControllerMSC
from src.monitor.collector import MetricsCollector
from src.monitor.exporter import write_csv, write_json
from src.monitor.report import render_report
from src.mpam.settings import SettingsTable
from src.noc.fabric import CallbackEndpoint, NocFabric
from src.scheduler.factory import build_policies
from src.traffic.generator import WorkloadGenerator
from src.traffic.request import Request
from src.traffic.requester import CoreOstdPool, RequesterRuntime

from .kernel import SimulationKernel


@dataclass
class SimulationResult:
    config: ProjectConfig
    collector: MetricsCollector
    elapsed_ns: float
    issued_requests: int
    completed_requests: int
    events_executed: int
    component_capabilities: List[Dict[str, object]]

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
            directory / "per_cpu_partid_mc.csv",
            self.collector.requester_mc_rows,
        )
        write_csv(
            directory / "per_partid_latency.csv",
            [{"partid": partid, **metrics} for partid, metrics in cumulative.items()],
        )
        write_csv(directory / "per_msc_utilization.csv", self.collector.msc_rows)
        write_csv(directory / "control_trace.csv", self.collector.control_rows)
        write_csv(
            directory / "control_events.csv",
            self.collector.control_rows,
        )
        write_csv(
            directory / "monitor_samples.csv",
            self.collector.monitor_sample_rows,
        )
        write_csv(directory / "timeline_trace.csv", self.collector.timeline_rows)
        write_json(
            directory / "component_capabilities.json",
            self.component_capabilities,
        )
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
        requesters_by_core: Dict[str, List] = {}
        for requester in config.requesters:
            core_id = requester.core or requester.id
            requesters_by_core.setdefault(core_id, []).append(
                requester
            )
        self.core_ostd_pools = {
            core_id: CoreOstdPool(
                core_id=core_id,
                max_outstanding=config.ostd.core_max_outstanding,
                policy=config.ostd.core_policy,
                thread_reserve=config.ostd.thread_reserve,
                thread_limits={
                    requester.id: requester.max_outstanding
                    for requester in requesters
                },
            )
            for core_id, requesters in requesters_by_core.items()
        }
        destination_mc_ids = tuple(
            item.id for item in config.memory_controllers
        )
        self.requesters = {
            item.id: RequesterRuntime(
                config=item,
                core_pool=self.core_ostd_pools[
                    item.core or item.id
                ],
                configured_partids=tuple(
                    sorted(
                        configured_partids_by_requester[item.id]
                    )
                ),
                destination_mc_ids=destination_mc_ids,
                cbusy_response_enable=(
                    config.ostd.cbusy_response_enable
                ),
            )
            for item in config.requesters
        }
        self._request_id = 0
        self._interval_index = 0
        self._control_event_sequence = 0
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
        required_ring_nodes = [
            *(f"r{index}" for index in range(config.noc.routers)),
            *(cache.id for cache in config.caches),
            *(mc.id for mc in config.memory_controllers),
        ]
        ring_node_order = tuple(
            config.noc.ring_node_order or required_ring_nodes
        )
        missing_ring_nodes = set(required_ring_nodes) - set(
            ring_node_order
        )
        if missing_ring_nodes:
            raise ValueError(
                "ring_node_order misses required nodes: "
                f"{sorted(missing_ring_nodes)}"
            )
        self.noc = NocFabric(
            self.kernel,
            config.noc,
            ring_node_order,
        )
        self.memory_controllers = {
            mc.id: MemoryControllerMSC(
                self.kernel,
                mc,
                self.settings_tables[mc.id],
                self._memory_service_complete,
                enforce_controls=self.enforce_controls,
                on_control_event=self._record_component_control_event,
            )
            for mc in config.memory_controllers
        }
        self.caches = {
            cache.id: CacheMSC(
                self.kernel,
                cache,
                self.settings_tables[cache.id],
                config.simulation.seed + 100 + index,
                self._cache_hit_complete,
                self._cache_miss,
                enforce_controls=self.enforce_controls,
                on_control_event=self._record_component_control_event,
            )
            for index, cache in enumerate(config.caches)
        }
        self.components = [
            self.noc,
            *self.caches.values(),
            *self.memory_controllers.values(),
        ]
        self.component_registry = ComponentRegistry()
        self.component_registry.register_all(self.components)
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
        self._generator_by_request = {
            (generator.requester.config.id, generator.workload.name): generator
            for generator in self.generators
        }

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
                        can_submit=(
                            lambda requester_id=requester_id:
                            self._can_submit(requester_id)
                        ),
                        on_submit_backpressure=(
                            lambda partid, delay_ns,
                            requester_id=requester_id:
                            self._record_source_ring_backpressure(
                                requester_id,
                                partid,
                                delay_ns,
                            )
                        ),
                        resolve_destination_mc=(
                            lambda address, requester_id=requester_id:
                            self._destination_mc_for(
                                requester_id,
                                address,
                            )
                        ),
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

    def _destination_mc_for(
        self,
        requester_id: str,
        address: int,
    ) -> str:
        interleave = self.config.address_interleave
        line = address // interleave.granularity_bytes
        if interleave.mode == "xor":
            line ^= address >> interleave.xor_shift
        index = line % len(self.config.memory_controllers)
        return self.config.memory_controllers[index].id

    def _requester_cache_id(self, requester_id: str) -> str:
        requester = self.config.requester_by_id[requester_id]
        return self.config.core_to_cache.get(
            requester.core or "",
            self.config.caches[0].id,
        )

    def _can_submit(self, requester_id: str) -> bool:
        requester = self.config.requester_by_id[requester_id]
        return self.noc.can_inject(
            requester.attach_node,
            self._requester_cache_id(requester_id),
            "req",
        )

    def _record_source_ring_backpressure(
        self,
        requester_id: str,
        partid: int,
        delay_ns: float,
    ) -> None:
        requester = self.config.requester_by_id[requester_id]
        cache_id = self._requester_cache_id(requester_id)
        self.noc.record_injection_backpressure(
            partid,
            delay_ns,
            "req",
            self.noc.route_direction(
                requester.attach_node,
                cache_id,
            ),
            requester.attach_node,
        )

    def _submit(self, request: Request) -> bool:
        requester = self.config.requester_by_id[request.requester_id]
        cache_id = self._requester_cache_id(request.requester_id)
        request.cache_id = cache_id
        request.destination_node = cache_id
        request.set_line_size(
            self.config.cache_by_id[cache_id].line_size
        )
        cache = self.caches[cache_id]
        return self.noc.transmit(
            request,
            "req",
            cache,
            source_node=requester.attach_node,
            destination_node=cache_id,
        )

    def _cache_miss(self, request: Request) -> None:
        mc_id = (
            request.memory_controller_id
            or self._destination_mc_for(
                request.requester_id,
                request.addr,
            )
        )
        request.memory_controller_id = mc_id
        request.destination_node = mc_id
        self._transmit_with_retry(
            request,
            "req",
            source_node=request.cache_id,
            destination_node=mc_id,
            downstream=self.memory_controllers[mc_id],
        )

    def _response_channel(self, request: Request) -> str:
        return "dat" if request.op == "read" else "rsp"

    def _cache_hit_complete(self, request: Request) -> None:
        requester = self.config.requester_by_id[request.requester_id]
        self._transmit_with_retry(
            request,
            self._response_channel(request),
            source_node=request.cache_id,
            destination_node=requester.attach_node,
            downstream=CallbackEndpoint(self._complete),
        )

    def _memory_service_complete(self, request: Request) -> None:
        cache = self.caches[request.cache_id]
        self._transmit_with_retry(
            request,
            self._response_channel(request),
            source_node=request.memory_controller_id,
            destination_node=request.cache_id,
            downstream=CallbackEndpoint(
                cache.accept_fill,
                readiness=cache.can_accept_fill,
            ),
        )

    def _transmit_with_retry(
        self,
        request: Request,
        channel: str,
        *,
        source_node: str,
        destination_node: str,
        downstream,
    ) -> None:
        if self.noc.transmit(
            request,
            channel,
            downstream,
            source_node=source_node,
            destination_node=destination_node,
        ):
            return
        retry_ns = self.noc.hop_delay_ns
        if channel == "req":
            request.timing.req_ring_delay_ns += retry_ns
        else:
            request.timing.rsp_dat_ring_delay_ns += retry_ns
        self.kernel.schedule(
            retry_ns,
            lambda: self._transmit_with_retry(
                request,
                channel,
                source_node=source_node,
                destination_node=destination_node,
                downstream=downstream,
            ),
            f"{channel}-ring-injection-retry",
        )

    def _complete(self, request: Request) -> None:
        self.requesters[request.requester_id].on_completion(
            request.partid,
            request.memory_controller_id,
        )
        generator = self._generator_by_request.get(
            (request.requester_id, request.workload_name)
        )
        if generator is not None:
            generator.on_complete(request)
        self.collector.on_complete(request, self.kernel.now_ns)
        if request.return_cbusy_source:
            mc_config = self.config.mc_by_id.get(
                request.return_cbusy_source
            )
            feedback_delay = (
                mc_config.cbusy_feedback_latency_ns
                if mc_config is not None
                else 0.0
            )
            self.kernel.schedule(
                feedback_delay,
                lambda request=request: self._deliver_return_cbusy(
                    request
                ),
                (
                    "cbusy-return-sideband:"
                    f"{request.return_cbusy_source}:"
                    f"p{request.partid}:"
                    f"{request.requester_id}"
                ),
            )

    def _deliver_return_cbusy(self, request: Request) -> None:
        msc_id = request.return_cbusy_source
        partid = request.partid
        level = max(0, min(3, int(request.return_cbusy_level)))
        cap = int(request.return_cbusy_ostd_cap or 0)
        requester = self.requesters[request.requester_id]
        key = (request.requester_id, partid)
        old_level = requester.cbusy_level(partid)
        old_cap = requester.effective_max_outstanding(partid)
        self._delivered_cbusy_levels[key] = level
        requester.set_cbusy(
            msc_id,
            partid,
            level,
            cap if level > 0 else requester.config.max_outstanding,
        )
        new_level = requester.cbusy_level(partid)
        new_cap = requester.effective_max_outstanding(partid)
        if old_level == 0 and new_level == 0:
            return
        self.collector.record_control(
            self._control_event(
                resource_id=msc_id,
                partid=partid,
                event_type="return_sideband_delivered",
                field="partid_cbusy_level",
                old_state=old_level,
                new_state=new_level,
                policy="mc_cbusy",
                reason=f"effective OSTD cap {new_cap}",
                monitor_sample_id=request.return_cbusy_monitor_sample_id,
                decision_id=request.return_cbusy_decision_id,
                action_effective_time_ns=self.kernel.now_ns,
                details={
                    "requester_id": request.requester_id,
                    "transaction_id": request.transaction_id,
                    "sample_time_ns": (
                        request.return_cbusy_sample_time_ns
                    ),
                    "feedback_source_msc": msc_id,
                    "source_cbusy_level": level,
                    "old_effective_ostd_cap": old_cap,
                    "effective_ostd_cap": new_cap,
                    "cpu_response_enable": (
                        requester.cbusy_response_enable
                    ),
                    "transport": "rsp_dat_sideband",
                },
            )
        )

    def _control_interval(self) -> None:
        self._interval_index += 1
        metrics = self.collector.capture_interval(
            self.kernel.now_ns,
            self.components,
            self.requesters.values(),
            capture_id=f"interval:{self._interval_index}",
        )
        for policy in self.policies:
            updates = policy.on_interval(self._interval_index, self.kernel.now_ns, metrics)
            for update_index, update in enumerate(updates):
                decision = update.with_context(
                    decision_id=(
                        f"decision:{self._interval_index}:"
                        f"{policy.name}:{update_index}"
                    ),
                    monitor_sample_id=self.collector.last_capture_id,
                    action_effective_time_ns=self.kernel.now_ns,
                )
                table = self.settings_tables.get(
                    decision.target_resource_id
                )
                if table is None:
                    continue
                old_value = table.update(
                    decision.partid,
                    decision.field,
                    decision.value,
                )
                self.collector.record_control(
                    self._control_event(
                        resource_id=decision.target_resource_id,
                        partid=decision.partid,
                        pmg=decision.pmg,
                        event_type="setting_applied",
                        field=decision.field,
                        old_state=old_value,
                        new_state=decision.value,
                        policy=decision.policy or policy.name,
                        reason=decision.reason,
                        monitor_sample_id=(
                            decision.monitor_sample_id
                        ),
                        decision_id=decision.decision_id,
                        action_effective_time_ns=(
                            decision.action_effective_time_ns
                        ),
                    )
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
                capture_id=f"final:{self._run_until_ns:g}",
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
            component_capabilities=(
                self.component_registry.to_dicts()
            ),
        )

    def _resource_type(self, resource_id: str) -> str:
        for descriptor in self.component_registry.descriptors():
            if descriptor.component_id == resource_id:
                return descriptor.component_type
        return "unknown"

    def _record_component_control_event(
        self,
        *,
        resource_id: str,
        partid: int,
        event_type: str,
        field: str,
        old_state: object,
        new_state: object,
        policy: str,
        reason: str,
        monitor_sample_id: str,
        decision_id: str,
        action_effective_time_ns: float,
        pmg: Optional[int] = None,
        details: Optional[Dict[str, object]] = None,
        outcome_state: str = "",
        outcome_reason: str = "",
    ) -> None:
        details = dict(details or {})
        if monitor_sample_id:
            self.collector.record_monitor_sample(
                MonitorSample(
                    time_ns=self.kernel.now_ns,
                    resource_type=self._resource_type(resource_id),
                    resource_id=resource_id,
                    local_cycle=details.get("local_cycle"),
                    partid=partid,
                    pmg=pmg,
                    metric=str(
                        details.get("control_input_metric")
                        or f"{field}_control_input"
                    ),
                    value=details.get("control_input_value"),
                    unit=str(details.get("control_input_unit") or "value"),
                    semantic=MetricSemantic.CONTROL_INPUT,
                    sample_id=monitor_sample_id,
                )
            )
        self.collector.record_control(
            self._control_event(
                resource_id=resource_id,
                partid=partid,
                pmg=pmg,
                event_type=event_type,
                field=field,
                old_state=old_state,
                new_state=new_state,
                policy=policy,
                reason=reason,
                monitor_sample_id=monitor_sample_id,
                decision_id=decision_id,
                action_effective_time_ns=action_effective_time_ns,
                details=details,
                outcome_state=outcome_state,
                outcome_reason=outcome_reason,
            )
        )

    def _control_event(
        self,
        resource_id: str,
        partid: int,
        event_type: str,
        field: str,
        old_state: object,
        new_state: object,
        policy: str,
        reason: str,
        monitor_sample_id: str = "",
        decision_id: str = "",
        action_effective_time_ns: Optional[float] = None,
        pmg: Optional[int] = None,
        details: Optional[Dict[str, object]] = None,
        outcome_state: str = "",
        outcome_reason: str = "",
    ) -> ControlEvent:
        self._control_event_sequence += 1
        return ControlEvent(
            event_id=f"control-event:{self._control_event_sequence}",
            event_time_ns=self.kernel.now_ns,
            resource_type=self._resource_type(resource_id),
            resource_id=resource_id,
            partid=partid,
            pmg=pmg,
            event_type=event_type,
            old_state=old_state,
            new_state=new_state,
            field=field,
            policy=policy,
            reason=reason,
            monitor_sample_id=monitor_sample_id,
            decision_id=decision_id,
            action_effective_time_ns=(
                self.kernel.now_ns
                if action_effective_time_ns is None
                else action_effective_time_ns
            ),
            details=details,
            outcome_state=outcome_state,
            outcome_reason=outcome_reason,
        )
