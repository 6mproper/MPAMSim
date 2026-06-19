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
        if cache.monitor_group_sets != 8:
            raise ConfigError(
                f"Cache {cache.id} monitor_group_sets must be 8 in this model"
            )
    for mc in config.memory_controllers:
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
    cores = []
    for cluster in config.clusters:
        if cluster.l3 not in cache_ids:
            raise ConfigError(f"Cluster {cluster.id} references unknown cache {cluster.l3}")
        cores.extend(cluster.cores)
    _ensure_unique(cores, "core")

    router_ids = {f"r{index}" for index in range(config.noc.routers)}
    for requester in config.requesters:
        if requester.max_outstanding <= 0:
            raise ConfigError(f"Requester {requester.id} max_outstanding must be positive")
        if requester.attach_node not in router_ids:
            raise ConfigError(f"Requester {requester.id} references unknown NoC node {requester.attach_node}")

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
            if control.priority is not None and not 0 <= control.priority <= 255:
                raise ConfigError("priority must be in [0, 255]")
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
                    cmax = (
                        control.cache_max_ways
                        if control.cache_max_ways is not None
                        else enabled_ways
                    )
                    if not 0 <= control.cache_min_ways <= cmax <= ways:
                        raise ConfigError(
                            f"MSC {entry.msc_id} requires 0 <= CMIN <= CMAX <= ways"
                        )
                    if cmax > enabled_ways:
                        raise ConfigError(
                            f"MSC {entry.msc_id} CMAX exceeds CPBM enabled ways"
                        )
