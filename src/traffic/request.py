from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Request:
    request_id: int
    workload_name: str
    workload_type: str
    requester_id: str
    partid: int
    pmg: int
    addr: int
    size_bytes: int
    op: str
    issue_time_ns: float
    working_set_bytes: int
    locality: str
    source_attach_node: str
    priority: int = 0
    qos_class: int = 0
    cache_id: str = ""
    memory_controller_id: str = ""
    noc_delay_ns: float = 0.0
    cache_delay_ns: float = 0.0
    cache_queue_delay_ns: float = 0.0
    mem_queue_delay_ns: float = 0.0
    mem_service_delay_ns: float = 0.0
    throttle_delay_ns: float = 0.0
    noc_enqueue_time_ns: float = 0.0
    cache_enqueue_time_ns: float = 0.0
    mem_enqueue_time_ns: float = 0.0
    cache_hit: bool = False

    @property
    def total_latency_ns(self) -> float:
        return (
            self.noc_delay_ns
            + self.cache_delay_ns
            + self.mem_queue_delay_ns
            + self.mem_service_delay_ns
            + self.throttle_delay_ns
        )
