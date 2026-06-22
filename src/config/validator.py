from __future__ import annotations

from typing import Iterable

from .schema import ProjectConfig


class ConfigError(ValueError):
    pass


def _ensure_unique(values: Iterable[str], label: str) -> None:
    values = list(values)
    if len(values) != len(set(values)):
        raise ConfigError(f"Duplicate {label} IDs are not allowed")


def validate_config(config: ProjectConfig) -> None:
    if config.simulation.time_ns <= 0:
        raise ConfigError("simulation.time_ns must be positive")
    if config.simulation.control_interval_ns <= 0:
        raise ConfigError("simulation.control_interval_ns must be positive")
    if not config.caches:
        raise ConfigError("At least one L3/SLC cache is required")
    if not config.memory_controllers:
        raise ConfigError("At least one memory controller is required")

    _ensure_unique((cluster.id for cluster in config.clusters), "cluster")
    _ensure_unique((cache.id for cache in config.caches), "cache")
    _ensure_unique((mc.id for mc in config.memory_controllers), "memory-controller")
    _ensure_unique((requester.id for requester in config.requesters), "requester")
    _ensure_unique((workload.name for workload in config.workloads), "workload")

    cache_ids = set(config.cache_by_id)
    for cache in config.caches:
        if cache.sets <= 0:
            raise ConfigError(f"Cache {cache.id} sets must be positive")
        if cache.ways <= 0:
            raise ConfigError(f"Cache {cache.id} ways must be positive")
        if cache.queue_depth <= 0:
            raise ConfigError(
                f"Cache {cache.id} queue_depth must be positive"
            )
        if cache.lookup_parallelism <= 0:
            raise ConfigError(
                f"Cache {cache.id} lookup_parallelism must be positive"
            )
        if cache.miss_detect_latency_ns <= 0:
            raise ConfigError(
                f"Cache {cache.id} miss_detect_latency_ns must be positive"
            )
        if cache.fill_latency_ns <= 0:
            raise ConfigError(
                f"Cache {cache.id} fill_latency_ns must be positive"
            )
        if cache.mshr_entries <= 0:
            raise ConfigError(
                f"Cache {cache.id} mshr_entries must be positive"
            )
        if cache.fill_buffer_entries <= 0:
            raise ConfigError(
                f"Cache {cache.id} fill_buffer_entries must be positive"
            )
        if cache.replacement_policy not in {"lru", "plru"}:
            raise ConfigError(
                f"Cache {cache.id} replacement_policy must be lru or plru"
            )
        if (
            cache.replacement_policy == "plru"
            and cache.ways & (cache.ways - 1)
        ):
            raise ConfigError(
                f"Cache {cache.id} PLRU requires power-of-two ways"
            )
        if cache.monitor_group_sets != 8:
            raise ConfigError(
                f"Cache {cache.id} monitor_group_sets must be 8 in this model"
            )
        if cache.clock_mhz <= 0:
            raise ConfigError(
                f"Cache {cache.id} clock must be positive"
            )
        if cache.monitor_period_cycles <= 0:
            raise ConfigError(
                f"Cache {cache.id} monitor period must be positive"
            )
        if (
            cache.history_weight < 0
            or cache.current_weight < 0
            or cache.history_weight + cache.current_weight != 256
        ):
            raise ConfigError(
                f"Cache {cache.id} monitor weights must be "
                "non-negative and sum to 256"
            )
    for mc in config.memory_controllers:
        if mc.clock_mhz <= 0:
            raise ConfigError(
                f"Memory controller {mc.id} clock must be positive"
            )
        if mc.monitor_period_cycles <= 0:
            raise ConfigError(
                f"Memory controller {mc.id} monitor period must be positive"
            )
        if (
            mc.history_weight < 0
            or mc.current_weight < 0
            or mc.history_weight + mc.current_weight != 256
        ):
            raise ConfigError(
                f"Memory controller {mc.id} monitor weights must be "
                "non-negative and sum to 256"
            )
        if not 0 <= mc.bandwidth_hysteresis < 1:
            raise ConfigError(
                f"Memory controller {mc.id} bandwidth hysteresis "
                "must be in [0, 1)"
            )
        if mc.aging_mode not in {
            "none",
            "per_partid_service_deficit",
        }:
            raise ConfigError(
                f"Memory controller {mc.id} aging_mode must be none "
                "or per_partid_service_deficit"
            )
        if mc.aging_quantum_cycles <= 0:
            raise ConfigError(
                f"Memory controller {mc.id} aging quantum must be positive"
            )
        if not 1 <= mc.aging_counter_bits <= 16:
            raise ConfigError(
                f"Memory controller {mc.id} aging counter bits "
                "must be in [1, 16]"
            )
        if not 0 <= mc.qos_aging_max_steps <= 7:
            raise ConfigError(
                f"Memory controller {mc.id} QoS aging steps must be in [0, 7]"
            )
        if not 0 <= mc.bmin_qos_promote <= 7:
            raise ConfigError(
                f"Memory controller {mc.id} BMIN QoS promotion must be in [0, 7]"
            )
        if not 0 <= mc.softlimit_qos_demote <= 7:
            raise ConfigError(
                f"Memory controller {mc.id} softlimit QoS demotion must be in [0, 7]"
            )
        if mc.cbusy_sample_ns <= 0:
            raise ConfigError(
                f"Memory controller {mc.id} CBusy sample must be positive"
            )
        if mc.cbusy_feedback_latency_ns < 0:
            raise ConfigError(
                f"Memory controller {mc.id} CBusy feedback latency cannot be negative"
            )
        if mc.cbusy_release_hold_samples <= 0:
            raise ConfigError(
                f"Memory controller {mc.id} CBusy release hold must be positive"
            )
        if not (
            0 < mc.cbusy_l1_bw_ratio
            <= mc.cbusy_l2_bw_ratio
            <= mc.cbusy_l3_bw_ratio
        ):
            raise ConfigError(
                f"Memory controller {mc.id} CBusy bandwidth thresholds must be ordered"
            )
        if not (
            0 <= mc.cbusy_l1_queue_ratio
            <= mc.cbusy_l2_queue_ratio
            <= mc.cbusy_l3_queue_ratio
            <= 1
        ):
            raise ConfigError(
                f"Memory controller {mc.id} CBusy queue thresholds must be ordered in [0, 1]"
            )
    interleave = config.address_interleave
    if interleave.mode not in {"linear", "xor"}:
        raise ConfigError(
            "Memory interleave mode must be linear or xor"
        )
    if (
        interleave.granularity_bytes <= 0
        or interleave.granularity_bytes
        & (interleave.granularity_bytes - 1)
    ):
        raise ConfigError(
            "Memory interleave granularity must be a positive power of two"
        )
    if not 0 <= interleave.xor_shift <= 63:
        raise ConfigError(
            "Memory interleave xor_shift must be in [0, 63]"
        )
    cores = []
    for cluster in config.clusters:
        if cluster.l3 not in cache_ids:
            raise ConfigError(f"Cluster {cluster.id} references unknown cache {cluster.l3}")
        cores.extend(cluster.cores)
    _ensure_unique(cores, "core")

    router_ids = {f"r{index}" for index in range(config.noc.routers)}
    if config.noc.clock_mhz <= 0:
        raise ConfigError("noc clock_mhz must be positive")
    if config.noc.flit_bytes <= 0:
        raise ConfigError("noc flit_bytes must be positive")
    if config.noc.link_slots_per_direction <= 0:
        raise ConfigError(
            "noc link_slots_per_direction must be positive"
        )
    if config.noc.hop_latency_cycles <= 0:
        raise ConfigError(
            "noc hop_latency_cycles must be positive"
        )
    if config.noc.tie_direction not in {"cw", "ccw"}:
        raise ConfigError("noc tie_direction must be cw or ccw")
    if (
        config.noc.ring_node_order
        and len(set(config.noc.ring_node_order))
        != len(config.noc.ring_node_order)
    ):
        raise ConfigError("noc ring_node_order must be unique")
    if config.noc.ring_node_order:
        required_ring_nodes = (
            router_ids
            | cache_ids
            | set(config.mc_by_id)
        )
        missing = required_ring_nodes - set(
            config.noc.ring_node_order
        )
        if missing:
            raise ConfigError(
                "noc ring_node_order misses required nodes: "
                f"{sorted(missing)}"
            )
    for requester in config.requesters:
        if requester.max_outstanding <= 0:
            raise ConfigError(f"Requester {requester.id} max_outstanding must be positive")
        if requester.attach_node not in router_ids:
            raise ConfigError(f"Requester {requester.id} references unknown NoC node {requester.attach_node}")
    if config.ostd.core_max_outstanding <= 0:
        raise ConfigError("core_max_outstanding must be positive")
    if config.ostd.core_policy not in {
        "shared",
        "static_partition",
        "reserve_borrow",
    }:
        raise ConfigError(
            "core_ostd_policy must be shared, static_partition, or reserve_borrow"
        )
    if not 1 <= config.ostd.thread_reserve <= config.ostd.core_max_outstanding:
        raise ConfigError(
            "thread_ostd_reserve must be in [1, core_max_outstanding]"
        )
    if (
        config.ostd.core_policy == "reserve_borrow"
        and (
            any(
                config.ostd.thread_reserve
                > requester.max_outstanding
                for requester in config.requesters
            )
            or config.ostd.thread_reserve
            * max(1, config.threads_per_core)
            > config.ostd.core_max_outstanding
        )
    ):
        raise ConfigError(
            "reserve_borrow requires thread_ostd_reserve <= each "
            "thread max and total reserves <= core_max_outstanding"
        )

    requester_ids = set(config.requester_by_id)
    for workload in config.workloads:
        if workload.partid not in config.partitions:
            raise ConfigError(f"Workload {workload.name} references undefined PARTID {workload.partid}")
        if not workload.requesters:
            raise ConfigError(f"Workload {workload.name} has no requesters")
        unknown = set(workload.requesters) - requester_ids
        if unknown:
            raise ConfigError(f"Workload {workload.name} references unknown requesters: {sorted(unknown)}")
        if workload.request_size_bytes <= 0:
            raise ConfigError(f"Workload {workload.name} request size must be positive")
        if not 0.0 <= workload.read_ratio <= 1.0:
            raise ConfigError(f"Workload {workload.name} read_ratio must be in [0, 1]")
        if (workload.injection_rate_mrps is None) == (workload.injection_rate_gbps is None):
            raise ConfigError(f"Workload {workload.name} must define exactly one injection rate")
        if workload.rate_scope not in {"aggregate", "per_requester"}:
            raise ConfigError(
                f"Workload {workload.name} injection scope must be aggregate or per_requester"
            )
        if workload.address_pattern not in {
            "auto",
            "sequential",
            "stream",
            "uniform_random",
            "random",
            "pointer_chase",
            "stride",
            "hotset",
        }:
            raise ConfigError(
                f"Workload {workload.name} address_pattern is unsupported"
            )
        if workload.operation_mix not in {"auto", "read", "write", "mixed"}:
            raise ConfigError(
                f"Workload {workload.name} operation_mix must be read, write, or mixed"
            )
        if workload.dependency_mode not in {
            "independent",
            "pointer_chain",
            "chained",
        }:
            raise ConfigError(
                f"Workload {workload.name} dependency_mode must be independent or pointer_chain"
            )
        if workload.arrival_mode not in {"fixed", "poisson", "burst"}:
            raise ConfigError(
                f"Workload {workload.name} arrival_mode must be fixed, poisson, or burst"
            )
        if workload.issue_selection not in {"fifo", "eligible_scan"}:
            raise ConfigError(
                f"Workload {workload.name} issue_selection must be fifo or eligible_scan"
            )
        if workload.independent_chains <= 0:
            raise ConfigError(
                f"Workload {workload.name} independent_chains must be positive"
            )
        if workload.source_queue_depth <= 0:
            raise ConfigError(
                f"Workload {workload.name} source_queue_depth must be positive"
            )
        if workload.eligible_scan_depth <= 0:
            raise ConfigError(
                f"Workload {workload.name} eligible_scan_depth must be positive"
            )
        if (
            workload.dependency_mode in {"pointer_chain", "chained"}
            and workload.operation_mix == "write"
        ):
            raise ConfigError(
                f"Workload {workload.name} pointer_chain requires read-capable traffic"
            )

    valid_msc_ids = cache_ids | set(config.mc_by_id) | {"noc"}
    for entry in config.msc_controls:
        if entry.msc_id not in valid_msc_ids:
            raise ConfigError(f"MPAM control references unknown MSC {entry.msc_id}")
        for control in entry.controls:
            if control.partid not in config.partitions:
                raise ConfigError(f"MSC {entry.msc_id} references undefined PARTID {control.partid}")
            if control.bw_max_gbps is not None and control.bw_max_gbps <= 0:
                raise ConfigError("bw_max_gbps must be positive")
            if control.bw_min_gbps is not None and control.bw_min_gbps < 0:
                raise ConfigError("bw_min_gbps cannot be negative")
            if (
                control.bw_min_gbps is not None
                and control.bw_max_gbps is not None
                and control.bw_min_gbps > control.bw_max_gbps
            ):
                raise ConfigError("BMIN cannot exceed BMAX")
            if control.bw_limit_mode not in {"softlimit", "hardlimit"}:
                raise ConfigError(
                    "bw_limit_mode must be softlimit or hardlimit"
                )
            if not 0 <= control.mc_qos <= 7:
                raise ConfigError("mc_qos must be in [0, 7]")
            if not (
                1
                <= control.cbusy_l3_ostd
                <= control.cbusy_l2_ostd
                <= control.cbusy_l1_ostd
            ):
                raise ConfigError(
                    "CBusy OSTD caps must satisfy 1 <= L3 <= L2 <= L1"
                )
            if control.cache_portion_bitmap is not None:
                try:
                    bitmap = int(control.cache_portion_bitmap, 16)
                except ValueError as exc:
                    raise ConfigError(f"Invalid cache portion bitmap {control.cache_portion_bitmap}") from exc
                if entry.msc_id in config.cache_by_id:
                    ways = config.cache_by_id[entry.msc_id].ways
                    if bitmap >= (1 << ways):
                        raise ConfigError(f"Cache mask for {entry.msc_id} exceeds {ways} ways")
                    enabled_ways = bin(bitmap).count("1")
                    reachable_percent = enabled_ways * 100.0 / ways
                    cmax = (
                        control.cache_max_percent
                        if control.cache_max_percent is not None
                        else 100.0
                    )
                    if not 0 <= control.cache_min_percent <= cmax <= 100:
                        raise ConfigError(
                            f"MSC {entry.msc_id} requires 0 <= CMIN <= CMAX <= 100%"
                        )
                    if control.cache_min_percent > reachable_percent + 1e-9:
                        raise ConfigError(
                            f"MSC {entry.msc_id} CMIN exceeds CPBM reachable capacity"
                        )
        if entry.msc_id in config.cache_by_id:
            enabled_cmin_total = sum(
                control.cache_min_percent
                for control in entry.controls
                if control.cmin_enable
            )
            if enabled_cmin_total > 100.0 + 1e-9:
                raise ConfigError(
                    f"MSC {entry.msc_id} enabled CMIN total exceeds 100%"
                )
