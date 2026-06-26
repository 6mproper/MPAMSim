from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .schema import (
    AddressInterleaveConfig,
    CacheConfig,
    ClusterConfig,
    MemoryControllerConfig,
    MPAMSettingConfig,
    MSCControlConfig,
    NocConfig,
    OstdConfig,
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
    workload_type = str(item.get("type", "stream"))
    arrival_mode = str(
        item.get(
            "arrival_mode",
            injection.get(
                "mode",
                item.get("injection_mode", "fixed"),
            ),
        )
    )
    address_pattern = str(
        item.get(
            "address_pattern",
            address.get(
                "pattern",
                item.get("address_distribution", "auto"),
            ),
        )
    )
    if address_pattern == "auto":
        address_pattern = {
            "stream": "sequential",
            "pointer_chase": "pointer_chase",
            "random_read": "uniform_random",
            "mixed_rw": "uniform_random",
            "bursty_dma": "sequential",
        }.get(workload_type, "uniform_random")
    dependency_mode = str(
        item.get(
            "dependency_mode",
            "pointer_chain"
            if workload_type == "pointer_chase"
            else "independent",
        )
    )
    read_ratio = float(item.get("read_ratio", 1.0))
    operation_mix = str(item.get("operation_mix", "auto"))
    if operation_mix == "auto":
        if read_ratio >= 1.0:
            operation_mix = "read"
        elif read_ratio <= 0.0:
            operation_mix = "write"
        else:
            operation_mix = "mixed"
    return WorkloadConfig(
        name=str(item["name"]),
        type=workload_type,
        requesters=[str(value) for value in item.get("requesters", [])],
        partid=int(item.get("partid", 0)),
        pmg=int(item.get("pmg", 0)),
        request_size_bytes=int(item.get("request_size_bytes", 64)),
        read_ratio=read_ratio,
        working_set_bytes=int(item.get("working_set_bytes", address.get("working_set_bytes", 1 << 20))),
        address_base_bytes=int(
            item.get("address_base_bytes", address.get("base_bytes", 0))
        ),
        target_p99_ns=float(item["target_p99_ns"]) if item.get("target_p99_ns") is not None else None,
        injection_rate_mrps=_optional_float(item.get("injection_rate_mrps", injection.get("rate_mrps"))),
        injection_rate_gbps=_optional_float(item.get("injection_rate_gbps", injection.get("rate_gbps"))),
        injection_mode=arrival_mode,
        rate_scope=str(injection.get("scope", item.get("injection_scope", "aggregate"))),
        burst_length=int(injection.get("burst_length", item.get("burst_length", 1))),
        burst_period_ns=_optional_float(injection.get("burst_period_ns", item.get("burst_period_ns"))),
        address_distribution=str(address.get("distribution", item.get("address_distribution", "auto"))),
        address_pattern=address_pattern,
        operation_mix=operation_mix,
        dependency_mode=dependency_mode,
        independent_chains=int(
            item.get("independent_chains", item.get("pointer_chains", 1))
        ),
        arrival_mode=arrival_mode,
        issue_selection=str(item.get("issue_selection", "fifo")),
        eligible_scan_depth=int(item.get("eligible_scan_depth", 1)),
        source_queue_depth=int(item.get("source_queue_depth", 1)),
        locality=str(address.get("locality", item.get("locality", "auto"))),
        start_ns=int(item.get("start_ns", 0)),
        stop_ns=int(item.get("stop_ns", simulation_time_ns)),
    )


def _optional_float(value: Any) -> Optional[float]:
    return None if value is None else float(value)


def _qos_value(
    item: Dict[str, Any],
    name: str,
    legacy_name: str,
    default: int,
) -> int:
    if name in item:
        return int(item[name])
    return max(0, min(7, int(item.get(legacy_name, default))))


def load_config(path: Union[str, Path], validate: bool = True) -> ProjectConfig:
    source_path = Path(path).resolve()
    raw = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be a mapping")

    simulation_raw = raw.get("simulation", {})
    simulation = SimulationConfig(
        time_ns=int(simulation_raw.get("time_ns", 1_000_000)),
        seed=int(simulation_raw.get("seed", 1)),
        control_interval_ns=int(simulation_raw.get("control_interval_ns", 128)),
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
            sampling_mode=str(item.get("sampling_mode", "fixed_first")),
            sampling_rotation_period_monitor_cycles=int(
                item.get("sampling_rotation_period_monitor_cycles", 1)
            ),
            queue_depth=int(item.get("queue_depth", 128)),
            lookup_parallelism=int(item.get("lookup_parallelism", 16)),
            miss_detect_latency_ns=float(
                item.get(
                    "miss_detect_latency_ns",
                    item.get("hit_latency_ns", 20.0),
                )
            ),
            fill_latency_ns=float(
                item.get("fill_latency_ns", 10.0)
            ),
            mshr_entries=int(item.get("mshr_entries", 64)),
            fill_buffer_entries=int(
                item.get("fill_buffer_entries", 16)
            ),
            merge_same_line_misses=bool(
                item.get("merge_same_line_misses", False)
            ),
            replacement_policy=str(
                item.get("replacement_policy", "lru")
            ),
            clock_mhz=float(item.get("clock_mhz", 1000.0)),
            monitor_period_cycles=int(
                item.get("monitor_period_cycles", 256)
            ),
            history_weight=float(item.get("history_weight", 0.75)),
            current_weight=float(item.get("current_weight", 0.25)),
            cbusy_response_enable=bool(
                item.get("cbusy_response_enable", True)
            ),
            qos_scheduler_enable=bool(
                item.get("qos_scheduler_enable", True)
            ),
            cbusy_qos_demote_per_level=int(
                item.get("cbusy_qos_demote_per_level", 1)
            ),
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
        clock_mhz=float(noc_raw.get("clock_mhz", 1000.0)),
        flit_bytes=int(noc_raw.get("flit_bytes", 16)),
        link_slots_per_direction=int(
            noc_raw.get("link_slots_per_direction", 1)
        ),
        hop_latency_cycles=int(
            noc_raw.get("hop_latency_cycles", 1)
        ),
        tie_direction=str(
            noc_raw.get("tie_direction", "cw")
        ),
        ring_node_order=[
            str(node)
            for node in noc_raw.get("ring_node_order", [])
        ],
    )
    memory_raw = soc.get("memory", {})
    memory_controllers = [
        MemoryControllerConfig(
            id=str(item["id"]),
            channels=int(item.get("channels", 1)),
            bandwidth_gbps_per_channel=float(item.get("bandwidth_gbps_per_channel", 64.0)),
            scheduler=str(item.get("scheduler", "priority_rr")),
            queue_depth=int(item.get("queue_depth", 512)),
            base_latency_ns=float(item.get("base_latency_ns", 80.0)),
            clock_mhz=float(item.get("clock_mhz", 1000.0)),
            monitor_period_cycles=int(
                item.get("monitor_period_cycles", 256)
            ),
            history_weight=float(item.get("history_weight", 0.95)),
            current_weight=float(item.get("current_weight", 0.05)),
            bandwidth_hysteresis=float(
                item.get("bandwidth_hysteresis", 0.05)
            ),
            aging_mode=str(item.get("aging_mode", "none")),
            aging_quantum_cycles=int(
                item.get("aging_quantum_cycles", 256)
            ),
            aging_counter_bits=int(
                item.get("aging_counter_bits", 3)
            ),
            token_bucket_window_ns=float(item.get("token_bucket_window_ns", 100.0)),
            aging_ns=float(item.get("aging_ns", 500.0)),
            qos_aging_max_steps=_qos_value(
                item, "qos_aging_max_steps", "aging_priority_cap", 3
            ),
            bmin_qos_promote=_qos_value(
                item, "bmin_qos_promote", "bmin_priority_boost", 2
            ),
            softlimit_qos_demote=_qos_value(
                item,
                "softlimit_qos_demote",
                "softlimit_priority_penalty",
                2,
            ),
            qos_map_8_to_4_enable=bool(
                item.get("qos_map_8_to_4_enable", False)
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
        for item in memory_raw.get("controllers", [])
    ]
    interleave_raw = memory_raw.get("interleave", {})
    address_interleave = AddressInterleaveConfig(
        mode=str(interleave_raw.get("mode", "linear")),
        granularity_bytes=int(
            interleave_raw.get("granularity_bytes", 256)
        ),
        xor_shift=int(interleave_raw.get("xor_shift", 12)),
    )

    requesters = _load_requesters(raw, clusters, threads_per_core)
    requester_section = raw.get("requesters", {})
    requester_defaults = requester_section.get("defaults", {})
    default_thread_ostd = int(
        requester_defaults.get("max_outstanding", 32)
    )
    ostd = OstdConfig(
        core_max_outstanding=int(
            requester_defaults.get(
                "core_max_outstanding",
                default_thread_ostd * max(1, threads_per_core),
            )
        ),
        core_policy=str(
            requester_defaults.get("core_ostd_policy", "shared")
        ),
        thread_reserve=int(
            requester_defaults.get("thread_ostd_reserve", 1)
        ),
        cbusy_response_enable=bool(
            requester_defaults.get("cbusy_response_enable", True)
        ),
    )

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
                cache_min_percent=float(
                    item.get(
                        "cmin_percent",
                        item.get("cmin", item.get("cache_min_percent", 0)),
                    )
                ),
                cache_max_percent=(
                    float(
                        item.get(
                            "cmax_percent",
                            item.get("cmax", item.get("cache_max_percent")),
                        )
                    )
                    if item.get(
                        "cmax_percent",
                        item.get("cmax", item.get("cache_max_percent")),
                    )
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
                mc_qos=_qos_value(item, "mc_qos", "priority", 0),
                monitor_enable=bool(item.get("monitor_enable", True)),
                cpbm_enable=bool(item.get("cpbm_enable", True)),
                cmin_enable=bool(item.get("cmin_enable", True)),
                cmax_enable=bool(item.get("cmax_enable", True)),
                bmin_enable=bool(item.get("bmin_enable", True)),
                bmax_enable=bool(item.get("bmax_enable", True)),
                mc_qos_enable=bool(
                    item.get("mc_qos_enable", item.get("priority_enable", True))
                ),
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
        address_interleave=address_interleave,
        requesters=requesters,
        ostd=ostd,
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
