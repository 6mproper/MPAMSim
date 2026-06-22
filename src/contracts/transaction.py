from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class Operation(str, Enum):
    READ = "read"
    WRITE = "write"


class RequestClass(str, Enum):
    DEMAND_READ = "demand_read"
    DEMAND_WRITE = "demand_write"
    PREFETCH = "prefetch"
    PAGE_WALK = "page_walk"
    WRITEBACK = "writeback"
    INSTRUCTION_FETCH = "instruction_fetch"
    MAINTENANCE = "maintenance"


class CompletionCondition(str, Enum):
    TERMINAL_RESPONSE = "terminal_response"
    READ_DATA = "read_data"
    WRITE_RESPONSE = "write_response"


@dataclass
class TransactionRoute:
    source_node: str = ""
    destination_node: str = ""
    cache_id: str = ""
    memory_controller_id: str = ""


@dataclass
class TransactionTiming:
    source_queue_delay_ns: float = 0.0
    ostd_cbusy_delay_ns: float = 0.0
    req_ring_delay_ns: float = 0.0
    cache_delay_ns: float = 0.0
    cache_queue_delay_ns: float = 0.0
    mshr_fill_delay_ns: float = 0.0
    mem_queue_delay_ns: float = 0.0
    mem_service_delay_ns: float = 0.0
    rsp_dat_ring_delay_ns: float = 0.0
    throttle_delay_ns: float = 0.0
    noc_enqueue_time_ns: float = 0.0
    cache_enqueue_time_ns: float = 0.0
    mem_enqueue_time_ns: float = 0.0
    completion_time_ns: Optional[float] = None

    @property
    def total_latency_ns(self) -> float:
        return (
            self.source_queue_delay_ns
            + self.ostd_cbusy_delay_ns
            + self.req_ring_delay_ns
            + self.cache_delay_ns
            + self.mshr_fill_delay_ns
            + self.mem_queue_delay_ns
            + self.mem_service_delay_ns
            + self.rsp_dat_ring_delay_ns
            + self.throttle_delay_ns
        )

    def as_dict(self) -> Dict[str, float]:
        return {
            "source_queue_delay_ns": self.source_queue_delay_ns,
            "ostd_cbusy_delay_ns": self.ostd_cbusy_delay_ns,
            "req_ring_delay_ns": self.req_ring_delay_ns,
            "cache_delay_ns": self.cache_delay_ns,
            "cache_queue_delay_ns": self.cache_queue_delay_ns,
            "mshr_fill_delay_ns": self.mshr_fill_delay_ns,
            "mem_queue_delay_ns": self.mem_queue_delay_ns,
            "mem_service_delay_ns": self.mem_service_delay_ns,
            "rsp_dat_ring_delay_ns": self.rsp_dat_ring_delay_ns,
            "throttle_delay_ns": self.throttle_delay_ns,
        }


@dataclass
class McArbitrationState:
    base_qos: int = 0
    effective_qos: int = 0
    aging_steps: int = 0
    bmin_promoted: bool = False
    soft_demoted: bool = False
    soft_over_limit: bool = False
    hard_blocked: bool = False
    selected_sequence: Optional[int] = None


@dataclass
class Transaction:
    transaction_id: int
    workload_name: str
    workload_type: str
    requester_id: str
    partid: int
    pmg: int
    address: int
    size_bytes: int
    operation: Operation
    issue_time_ns: float
    working_set_bytes: int
    locality: str
    source_node: str
    core_id: str = ""
    thread_id: int = 0
    parent_transaction_id: Optional[int] = None
    line_address: Optional[int] = None
    request_class: Optional[RequestClass] = None
    completion_condition: CompletionCondition = (
        CompletionCondition.TERMINAL_RESPONSE
    )
    priority: int = 0
    qos_class: int = 0
    route: TransactionRoute = field(default_factory=TransactionRoute)
    timing: TransactionTiming = field(default_factory=TransactionTiming)
    mc_arbitration: McArbitrationState = field(
        default_factory=McArbitrationState
    )
    cache_hit: bool = False
    carry_cbusy_level: int = 0

    def __setattr__(self, name: str, value: object) -> None:
        declared = name in getattr(type(self), "__dataclass_fields__", {})
        descriptor = getattr(type(self), name, None)
        if not declared and not isinstance(descriptor, property):
            raise AttributeError(
                f"Transaction field is not declared: {name}"
            )
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        if not isinstance(self.operation, Operation):
            self.operation = Operation(str(self.operation))
        if self.request_class is None:
            self.request_class = (
                RequestClass.DEMAND_READ
                if self.operation == Operation.READ
                else RequestClass.DEMAND_WRITE
            )
        elif not isinstance(self.request_class, RequestClass):
            self.request_class = RequestClass(str(self.request_class))
        if not isinstance(
            self.completion_condition,
            CompletionCondition,
        ):
            self.completion_condition = CompletionCondition(
                str(self.completion_condition)
            )
        if not self.route.source_node:
            self.route.source_node = self.source_node

    @property
    def request_id(self) -> int:
        return self.transaction_id

    @property
    def addr(self) -> int:
        return self.address

    @property
    def op(self) -> str:
        return self.operation.value

    @property
    def source_attach_node(self) -> str:
        return self.route.source_node

    @property
    def cache_id(self) -> str:
        return self.route.cache_id

    @cache_id.setter
    def cache_id(self, value: str) -> None:
        self.route.cache_id = value

    @property
    def memory_controller_id(self) -> str:
        return self.route.memory_controller_id

    @memory_controller_id.setter
    def memory_controller_id(self, value: str) -> None:
        self.route.memory_controller_id = value

    @property
    def destination_node(self) -> str:
        return self.route.destination_node

    @destination_node.setter
    def destination_node(self, value: str) -> None:
        self.route.destination_node = value

    @property
    def noc_delay_ns(self) -> float:
        return self.timing.req_ring_delay_ns

    @noc_delay_ns.setter
    def noc_delay_ns(self, value: float) -> None:
        self.timing.req_ring_delay_ns = value

    @property
    def cache_delay_ns(self) -> float:
        return self.timing.cache_delay_ns

    @cache_delay_ns.setter
    def cache_delay_ns(self, value: float) -> None:
        self.timing.cache_delay_ns = value

    @property
    def cache_queue_delay_ns(self) -> float:
        return self.timing.cache_queue_delay_ns

    @cache_queue_delay_ns.setter
    def cache_queue_delay_ns(self, value: float) -> None:
        self.timing.cache_queue_delay_ns = value

    @property
    def mem_queue_delay_ns(self) -> float:
        return self.timing.mem_queue_delay_ns

    @mem_queue_delay_ns.setter
    def mem_queue_delay_ns(self, value: float) -> None:
        self.timing.mem_queue_delay_ns = value

    @property
    def mem_service_delay_ns(self) -> float:
        return self.timing.mem_service_delay_ns

    @mem_service_delay_ns.setter
    def mem_service_delay_ns(self, value: float) -> None:
        self.timing.mem_service_delay_ns = value

    @property
    def throttle_delay_ns(self) -> float:
        return self.timing.throttle_delay_ns

    @throttle_delay_ns.setter
    def throttle_delay_ns(self, value: float) -> None:
        self.timing.throttle_delay_ns = value

    @property
    def noc_enqueue_time_ns(self) -> float:
        return self.timing.noc_enqueue_time_ns

    @noc_enqueue_time_ns.setter
    def noc_enqueue_time_ns(self, value: float) -> None:
        self.timing.noc_enqueue_time_ns = value

    @property
    def cache_enqueue_time_ns(self) -> float:
        return self.timing.cache_enqueue_time_ns

    @cache_enqueue_time_ns.setter
    def cache_enqueue_time_ns(self, value: float) -> None:
        self.timing.cache_enqueue_time_ns = value

    @property
    def mem_enqueue_time_ns(self) -> float:
        return self.timing.mem_enqueue_time_ns

    @mem_enqueue_time_ns.setter
    def mem_enqueue_time_ns(self, value: float) -> None:
        self.timing.mem_enqueue_time_ns = value

    @property
    def total_latency_ns(self) -> float:
        return self.timing.total_latency_ns

    def set_line_size(self, line_size: int) -> None:
        if line_size <= 0:
            raise ValueError("line_size must be positive")
        self.line_address = (
            self.address // line_size
        ) * line_size

    def mark_complete(self, completion_time_ns: float) -> None:
        self.timing.completion_time_ns = completion_time_ns
