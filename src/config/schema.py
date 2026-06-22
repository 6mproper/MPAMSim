from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SimulationConfig:
    time_ns: int
    seed: int = 1
    control_interval_ns: int = 100_000


@dataclass
class ClusterConfig:
    id: str
    cores: List[str]
    l3: str


@dataclass
class CacheConfig:
    id: str
    level: str
    size_bytes: int
    line_size: int
    ways: int
    shared_by_cores: List[str]
    hit_latency_ns: float = 20.0
    sets: int = 1024
    monitor_group_sets: int = 8
    queue_depth: int = 128
    lookup_parallelism: int = 16
    miss_detect_latency_ns: float = 20.0
    fill_latency_ns: float = 10.0
    mshr_entries: int = 64
    fill_buffer_entries: int = 16
    merge_same_line_misses: bool = True
    replacement_policy: str = "lru"
    clock_mhz: float = 1000.0
    monitor_period_cycles: int = 256
    history_weight: int = 192
    current_weight: int = 64


@dataclass
class NocConfig:
    topology: str
    routers: int
    link_bandwidth_gbps: float
    router_latency_ns: float
    queue_depth: int
    virtual_channels: int
    average_hops: int = 2
    clock_mhz: float = 1000.0
    flit_bytes: int = 16
    link_slots_per_direction: int = 1
    hop_latency_cycles: int = 1
    tie_direction: str = "cw"
    ring_node_order: List[str] = field(default_factory=list)


@dataclass
class MemoryControllerConfig:
    id: str
    channels: int
    bandwidth_gbps_per_channel: float
    scheduler: str
    queue_depth: int = 512
    base_latency_ns: float = 80.0
    clock_mhz: float = 1000.0
    monitor_period_cycles: int = 256
    history_weight: int = 192
    current_weight: int = 64
    bandwidth_hysteresis: float = 0.05
    aging_mode: str = "none"
    aging_quantum_cycles: int = 256
    aging_counter_bits: int = 3
    # Retained only so older YAML files continue to load.
    token_bucket_window_ns: float = 100.0
    aging_ns: float = 500.0
    qos_aging_max_steps: int = 3
    bmin_qos_promote: int = 2
    softlimit_qos_demote: int = 2
    cbusy_sample_ns: float = 1_000.0
    cbusy_feedback_latency_ns: float = 50.0
    cbusy_release_hold_samples: int = 3
    cbusy_l1_bw_ratio: float = 1.0
    cbusy_l2_bw_ratio: float = 1.1
    cbusy_l3_bw_ratio: float = 1.25
    cbusy_l1_queue_ratio: float = 0.25
    cbusy_l2_queue_ratio: float = 0.50
    cbusy_l3_queue_ratio: float = 0.75


@dataclass
class AddressInterleaveConfig:
    mode: str = "linear"
    granularity_bytes: int = 256
    xor_shift: int = 12


@dataclass
class RequesterConfig:
    id: str
    type: str
    attach_node: str
    max_outstanding: int
    cluster: Optional[str] = None
    core: Optional[str] = None
    thread: Optional[int] = None


@dataclass
class OstdConfig:
    core_max_outstanding: int
    core_policy: str = "shared"
    thread_reserve: int = 1


@dataclass
class MPAMSettingConfig:
    partid: int
    cache_portion_bitmap: Optional[str] = None
    cache_min_percent: float = 0.0
    cache_max_percent: Optional[float] = None
    bw_max_gbps: Optional[float] = None
    bw_min_gbps: Optional[float] = None
    bw_limit_mode: str = "hardlimit"
    mc_qos: int = 0
    monitor_enable: bool = True
    cpbm_enable: bool = True
    cmin_enable: bool = True
    cmax_enable: bool = True
    bmin_enable: bool = True
    bmax_enable: bool = True
    mc_qos_enable: bool = True
    cbusy_enable: bool = False
    cbusy_l1_ostd: int = 24
    cbusy_l2_ostd: int = 12
    cbusy_l3_ostd: int = 4


@dataclass
class MSCControlConfig:
    msc_id: str
    controls: List[MPAMSettingConfig]


@dataclass
class WorkloadConfig:
    name: str
    type: str
    requesters: List[str]
    partid: int
    pmg: int
    request_size_bytes: int
    read_ratio: float
    working_set_bytes: int
    target_p99_ns: Optional[float] = None
    injection_rate_mrps: Optional[float] = None
    injection_rate_gbps: Optional[float] = None
    injection_mode: str = "fixed"
    rate_scope: str = "aggregate"
    burst_length: int = 1
    burst_period_ns: Optional[float] = None
    address_distribution: str = "auto"
    locality: str = "auto"
    start_ns: int = 0
    stop_ns: Optional[int] = None


@dataclass
class PolicyConfig:
    name: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputConfig:
    dir: str
    formats: List[str] = field(default_factory=lambda: ["json", "csv"])
    trace_requests: bool = False
    generate_report: bool = True
    report_format: str = "html"
    plots: List[str] = field(default_factory=list)


@dataclass
class ProjectConfig:
    simulation: SimulationConfig
    clusters: List[ClusterConfig]
    threads_per_core: int
    caches: List[CacheConfig]
    noc: NocConfig
    memory_controllers: List[MemoryControllerConfig]
    address_interleave: AddressInterleaveConfig
    requesters: List[RequesterConfig]
    ostd: OstdConfig
    partid_width: int
    pmg_width: int
    partitions: Dict[int, str]
    msc_controls: List[MSCControlConfig]
    workloads: List[WorkloadConfig]
    policies: List[PolicyConfig]
    outputs: OutputConfig
    source_path: Path
    raw: Dict[str, Any]

    @property
    def cache_by_id(self) -> Dict[str, CacheConfig]:
        return {cache.id: cache for cache in self.caches}

    @property
    def mc_by_id(self) -> Dict[str, MemoryControllerConfig]:
        return {mc.id: mc for mc in self.memory_controllers}

    @property
    def requester_by_id(self) -> Dict[str, RequesterConfig]:
        return {requester.id: requester for requester in self.requesters}

    @property
    def core_to_cache(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for cluster in self.clusters:
            for core in cluster.cores:
                result[core] = cluster.l3
        return result

    @property
    def controls_by_msc(self) -> Dict[str, List[MPAMSettingConfig]]:
        return {entry.msc_id: entry.controls for entry in self.msc_controls}
