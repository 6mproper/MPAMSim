from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .schema import (
    CacheConfig,
    ClusterConfig,
    MemoryControllerConfig,
    MPAMSettingConfig,
    MSCControlConfig,
    NocConfig,
    OutputConfig,
    PolicyConfig,
    ProjectConfig,
    RequesterConfig,
    SimulationConfig,
    WorkloadConfig,
)
from .validator import validate_config


def _load_requesters(raw: Dict[str, Any], clusters: List[ClusterConfig], threads_per_core: int) -> List[RequesterConfig]:
    section = raw.get("requesters", {})
    defaults = section.get("defaults", {})
    default_outstanding = int(defaults.get("max_outstanding", 32))
    attach_nodes = section.get("core_attach_nodes", {})
    requesters: List[RequesterConfig] = []

    if section.get("auto_expand_cpu_threads", True):
        for cluster in clusters:
            for core in cluster.cores:
                attach_node = str(attach_nodes.get(core, "r0"))
                for thread in range(threads_per_core):
                    requesters.append(
                        RequesterConfig(
                            id=f"{core}.t{thread}",
                            type="cpu_thread",
                            cluster=cluster.id,
                            core=core,
                            thread=thread,
                            attach_node=attach_node,
                            max_outstanding=default_outstanding,
                        )
                    )

    explicit = section.get("explicit", [])
    if isinstance(section, list):
        explicit = section
    for item in explicit:
        requesters.append(
            RequesterConfig(
                id=str(item["id"]),
                type=str(item.get("type", "synthetic_tenant")),
                cluster=item.get("cluster"),
                core=item.get("core"),
                thread=item.get("thread"),
                attach_node=str(item.get("attach_node", "r0")),
                max_outstanding=int(item.get("max_outstanding", default_outstanding)),
            )
        )
    return requesters


def _load_workload(item: Dict[str, Any], simulation_time_ns: int) -> WorkloadConfig:
    injection = item.get("injection", {})
    address = item.get("address", {})
    return WorkloadConfig(
        name=str(item["name"]),
        type=str(item.get("type", "stream")),
        requesters=[str(value) for value in item.get("requesters", [])],
        partid=int(item.get("partid", 0)),
        pmg=int(item.get("pmg", 0)),
        request_size_bytes=int(item.get("request_size_bytes", 64)),
        read_ratio=float(item.get("read_ratio", 1.0)),
        working_set_bytes=int(item.get("working_set_bytes", address.get("working_set_bytes", 1 << 20))),
        target_p99_ns=float(item["target_p99_ns"]) if item.get("target_p99_ns") is not None else None,
        injection_rate_mrps=_optional_float(item.get("injection_rate_mrps", injection.get("rate_mrps"))),
        injection_rate_gbps=_optional_float(item.get("injection_rate_gbps", injection.get("rate_gbps"))),
        injection_mode=str(injection.get("mode", item.get("injection_mode", "fixed"))),
        rate_scope=str(injection.get("scope", item.get("injection_scope", "aggregate"))),
        burst_length=int(injection.get("burst_length", item.get("burst_length", 1))),
        burst_period_ns=_optional_float(injection.get("burst_period_ns", item.get("burst_period_ns"))),
        address_distribution=str(address.get("distribution", item.get("address_distribution", "auto"))),
        locality=str(address.get("locality", item.get("locality", "auto"))),
        start_ns=int(item.get("start_ns", 0)),
        stop_ns=int(item.get("stop_ns", simulation_time_ns)),
    )


def _optional_float(value: Any) -> Optional[float]:
    return None if value is None else float(value)


def load_config(path: Union[str, Path], validate: bool = True) -> ProjectConfig:
    source_path = Path(path).resolve()
    raw = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be a mapping")

    simulation_raw = raw.get("simulation", {})
    simulation = SimulationConfig(
        time_ns=int(simulation_raw.get("time_ns", 1_000_000)),
        seed=int(simulation_raw.get("seed", 1)),
        control_interval_ns=int(simulation_raw.get("control_interval_ns", 100_000)),
    )

    soc = raw.get("soc", {})
    clusters = [
        ClusterConfig(id=str(item["id"]), cores=[str(core) for core in item.get("cores", [])], l3=str(item["l3"]))
        for item in soc.get("clusters", [])
    ]
    threads_per_core = int(soc.get("core", {}).get("threads_per_core", 1))
    caches = [
        CacheConfig(
            id=str(item["id"]),
            level=str(item.get("level", "L3")),
            size_bytes=int(item["size_bytes"]),
            line_size=int(item.get("line_size", 64)),
            ways=int(item.get("ways", 16)),
            shared_by_cores=[str(core) for core in item.get("shared_by_cores", [])],
            hit_latency_ns=float(item.get("hit_latency_ns", 20.0)),
            sets=int(
                item.get(
                    "sets",
                    max(
                        1,
                        int(item["size_bytes"])
                        // (
                            int(item.get("line_size", 64))
                            * int(item.get("ways", 16))
                        ),
                    ),
                )
            ),
            monitor_group_sets=int(item.get("monitor_group_sets", 8)),
            queue_depth=int(item.get("queue_depth", 128)),
            lookup_parallelism=int(item.get("lookup_parallelism", 16)),
        )
        for item in soc.get("caches", [])
    ]
    noc_raw = soc.get("noc", {})
    noc = NocConfig(
        topology=str(noc_raw.get("topology", "mesh")),
        routers=int(noc_raw.get("routers", 1)),
        link_bandwidth_gbps=float(noc_raw.get("link_bandwidth_gbps", 128.0)),
        router_latency_ns=float(noc_raw.get("router_latency_ns", 5.0)),
        queue_depth=int(noc_raw.get("queue_depth", 64)),
        virtual_channels=int(noc_raw.get("virtual_channels", 1)),
        average_hops=int(noc_raw.get("average_hops", 2)),
    )
    memory_controllers = [
        MemoryControllerConfig(
            id=str(item["id"]),
            channels=int(item.get("channels", 1)),
            bandwidth_gbps_per_channel=float(item.get("bandwidth_gbps_per_channel", 64.0)),
            scheduler=str(item.get("scheduler", "priority_rr")),
            queue_depth=int(item.get("queue_depth", 512)),
            base_latency_ns=float(item.get("base_latency_ns", 80.0)),
            token_bucket_window_ns=float(item.get("token_bucket_window_ns", 100.0)),
            aging_ns=float(item.get("aging_ns", 500.0)),
            aging_priority_cap=int(item.get("aging_priority_cap", 15)),
            bmin_priority_boost=int(item.get("bmin_priority_boost", 16)),
            softlimit_priority_penalty=int(
                item.get("softlimit_priority_penalty", 16)
            ),
            cbusy_sample_ns=float(item.get("cbusy_sample_ns", 1_000.0)),
            cbusy_feedback_latency_ns=float(
                item.get("cbusy_feedback_latency_ns", 50.0)
            ),
            cbusy_release_hold_samples=int(
                item.get("cbusy_release_hold_samples", 3)
            ),
            cbusy_l1_bw_ratio=float(item.get("cbusy_l1_bw_ratio", 1.0)),
            cbusy_l2_bw_ratio=float(item.get("cbusy_l2_bw_ratio", 1.1)),
            cbusy_l3_bw_ratio=float(item.get("cbusy_l3_bw_ratio", 1.25)),
            cbusy_l1_queue_ratio=float(
                item.get("cbusy_l1_queue_ratio", 0.25)
            ),
            cbusy_l2_queue_ratio=float(
                item.get("cbusy_l2_queue_ratio", 0.50)
            ),
            cbusy_l3_queue_ratio=float(
                item.get("cbusy_l3_queue_ratio", 0.75)
            ),
        )
        for item in soc.get("memory", {}).get("controllers", [])
    ]

    requesters = _load_requesters(raw, clusters, threads_per_core)

    mpam = raw.get("mpam", {})
    partitions = {int(item["partid"]): str(item.get("name", item["partid"])) for item in mpam.get("partitions", [])}
    msc_controls = []
    for entry in mpam.get("msc_controls", []):
        controls = [
            MPAMSettingConfig(
                partid=int(item["partid"]),
                cache_portion_bitmap=item.get(
                    "cpbm", item.get("cache_portion_bitmap")
                ),
                cache_min_ways=int(
                    item.get("cmin", item.get("cache_min_ways", 0))
                ),
                cache_max_ways=(
                    int(item.get("cmax", item.get("cache_max_ways")))
                    if item.get("cmax", item.get("cache_max_ways"))
                    is not None
                    else None
                ),
                bw_max_gbps=_optional_float(
                    item.get("bmax", item.get("bw_max_gbps"))
                ),
                bw_min_gbps=_optional_float(
                    item.get("bmin", item.get("bw_min_gbps"))
                ),
                bw_limit_mode=str(
                    item.get(
                        "limit_mode",
                        item.get("bw_limit_mode", "hardlimit"),
                    )
                ),
                priority=int(item["priority"]) if item.get("priority") is not None else None,
                monitor_enable=bool(item.get("monitor_enable", True)),
                cpbm_enable=bool(item.get("cpbm_enable", True)),
                cmin_enable=bool(item.get("cmin_enable", True)),
                cmax_enable=bool(item.get("cmax_enable", True)),
                bmin_enable=bool(item.get("bmin_enable", True)),
                bmax_enable=bool(item.get("bmax_enable", True)),
                priority_enable=bool(item.get("priority_enable", True)),
                cbusy_enable=bool(item.get("cbusy_enable", False)),
                cbusy_l1_ostd=int(item.get("cbusy_l1_ostd", 24)),
                cbusy_l2_ostd=int(item.get("cbusy_l2_ostd", 12)),
                cbusy_l3_ostd=int(item.get("cbusy_l3_ostd", 4)),
            )
            for item in entry.get("controls", [])
        ]
        msc_controls.append(MSCControlConfig(msc_id=str(entry["msc_id"]), controls=controls))

    workloads = [_load_workload(item, simulation.time_ns) for item in raw.get("workloads", [])]
    policies = [
        PolicyConfig(name=str(item) if isinstance(item, str) else str(item["name"]), params={} if isinstance(item, str) else dict(item.get("params", {})))
        for item in raw.get("policies", [])
    ]
    output_raw = raw.get("outputs", {})
    visual = output_raw.get("visualization", {})
    outputs = OutputConfig(
        dir=str(output_raw.get("dir", "outputs/run")),
        formats=[str(value) for value in output_raw.get("formats", ["json", "csv"])],
        trace_requests=bool(output_raw.get("trace_requests", False)),
        generate_report=bool(visual.get("generate_report", True)),
        report_format=str(visual.get("report_format", "html")),
        plots=[str(value) for value in visual.get("plots", [])],
    )

    config = ProjectConfig(
        simulation=simulation,
        clusters=clusters,
        threads_per_core=threads_per_core,
        caches=caches,
        noc=noc,
        memory_controllers=memory_controllers,
        requesters=requesters,
        partid_width=int(mpam.get("partid_width", 8)),
        pmg_width=int(mpam.get("pmg_width", 8)),
        partitions=partitions,
        msc_controls=msc_controls,
        workloads=workloads,
        policies=policies,
        outputs=outputs,
        source_path=source_path,
        raw=raw,
    )
    if validate:
        validate_config(config)
    return config
