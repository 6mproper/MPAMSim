from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, DefaultDict, Deque, Dict, List, Tuple

from src.config.schema import NocConfig
from src.contracts.flit import RingChannel, RingDirection, RingFlit
from src.contracts.interfaces import EndpointPort
from src.sim.component import Component
from src.sim.kernel import SimulationKernel
from src.traffic.request import Request


@dataclass
class CallbackEndpoint:
    accept_callback: Callable[[Request], None]
    readiness: Callable[[Request], bool] = lambda _request: True

    def can_accept(self, transaction: Request) -> bool:
        return bool(self.readiness(transaction))

    def accept(self, transaction: Request) -> None:
        self.accept_callback(transaction)


@dataclass
class TransferState:
    transfer_id: int
    transaction: Request
    channel: RingChannel
    direction: RingDirection
    source_node: str
    destination_node: str
    endpoint: EndpointPort
    flit_count: int
    created_time_ns: float
    pending_flits: Deque[RingFlit] = field(default_factory=deque)
    ejected_flits: int = 0


def _ring_counters() -> Dict[str, float]:
    return {
        "offered_flits": 0,
        "injected_flits": 0,
        "ejected_flits": 0,
        "failed_ejections": 0,
        "full_laps": 0,
        "hops": 0,
        "injection_backpressure_events": 0,
        "injection_backpressure_ns": 0.0,
        "completed_transfers": 0,
    }


class NocFabric(Component):
    inputs = ("Transaction", "EndpointPort")
    outputs = ("Transaction", "MonitorSnapshot")
    capabilities = (
        "bufferless_ring_transport",
        "three_independent_channels",
        "bidirectional_shortest_path",
        "dat_flit_reassembly",
        "neutral_request_arbitration",
        "per_partid_monitoring",
    )
    required_monitors = (
        "slot_occupancy",
        "injection_backpressure",
        "failed_ejection",
        "recirculation",
        "per_partid_delay",
    )
    actions = (
        "inject_flit",
        "advance_hop",
        "eject_flit",
        "recirculate_flit",
        "reassemble_transfer",
    )
    validation_hooks = (
        "link_slot_capacity",
        "continuous_movement",
        "deterministic_route",
        "flit_conservation",
    )
    incompatible_capabilities = ("queued_noc_transport",)
    approximations = (
        "CHI-shaped REQ/RSP/DAT channels without full CHI opcodes",
        "endpoint source injection state is not a ring buffer",
        "SNP channel is reserved and disabled",
    )

    CHANNELS: Tuple[RingChannel, ...] = ("req", "rsp", "dat")
    DIRECTIONS: Tuple[RingDirection, ...] = ("cw", "ccw")

    def __init__(
        self,
        kernel: SimulationKernel,
        config: NocConfig,
        node_order: Tuple[str, ...],
    ) -> None:
        super().__init__("noc", "noc")
        if len(node_order) < 2:
            raise ValueError("Bufferless ring requires at least two nodes")
        if len(set(node_order)) != len(node_order):
            raise ValueError("Bufferless ring node order must be unique")
        self.kernel = kernel
        self.config = config
        self.node_order = node_order
        self.node_index = {
            node_id: index
            for index, node_id in enumerate(node_order)
        }
        self._links: Dict[
            Tuple[RingChannel, RingDirection],
            List[List[RingFlit]],
        ] = {
            (channel, direction): [
                [] for _ in self.node_order
            ]
            for channel in self.CHANNELS
            for direction in self.DIRECTIONS
        }
        self._transfers: Dict[int, TransferState] = {}
        self._pending_transfer_ids: Deque[int] = deque()
        self._transfer_sequence = 0
        self._tick_scheduled = False
        self._interval = _ring_counters()
        self._per_partid: DefaultDict[
            int, Dict[str, float]
        ] = defaultdict(_ring_counters)
        self._per_channel_direction: DefaultDict[
            Tuple[str, str], Dict[str, float]
        ] = defaultdict(_ring_counters)
        self._per_partid_channel_direction: DefaultDict[
            Tuple[int, str, str], Dict[str, float]
        ] = defaultdict(_ring_counters)
        self._per_link: DefaultDict[
            Tuple[str, str, int], Dict[str, float]
        ] = defaultdict(_ring_counters)
        self._per_node: DefaultDict[
            str, Dict[str, float]
        ] = defaultdict(_ring_counters)
        self._slot_sample_sum = 0
        self._slot_samples = 0
        self._in_flight_peak = 0

    @property
    def hop_delay_ns(self) -> float:
        return (
            self.config.hop_latency_cycles
            * 1000.0
            / self.config.clock_mhz
        )

    @property
    def total_slots(self) -> int:
        return (
            len(self.CHANNELS)
            * len(self.DIRECTIONS)
            * len(self.node_order)
            * self.config.link_slots_per_direction
        )

    @property
    def in_flight_flits(self) -> int:
        return sum(
            len(link)
            for links in self._links.values()
            for link in links
        )

    def _normalize_endpoint(
        self,
        downstream: EndpointPort | Callable[[Request], None],
    ) -> EndpointPort:
        if hasattr(downstream, "can_accept") and hasattr(
            downstream,
            "accept",
        ):
            return downstream  # type: ignore[return-value]
        return CallbackEndpoint(downstream)  # type: ignore[arg-type]

    def _direction(
        self,
        source_node: str,
        destination_node: str,
    ) -> RingDirection:
        source = self.node_index[source_node]
        destination = self.node_index[destination_node]
        count = len(self.node_order)
        clockwise = (destination - source) % count
        counter_clockwise = (source - destination) % count
        if clockwise < counter_clockwise:
            return "cw"
        if counter_clockwise < clockwise:
            return "ccw"
        return self.config.tie_direction

    def route_direction(
        self,
        source_node: str,
        destination_node: str,
    ) -> RingDirection:
        self._validate_route(source_node, destination_node, "req")
        return self._direction(source_node, destination_node)

    def _outgoing_link(self, source_node: str) -> int:
        return self.node_index[source_node]

    def can_inject(
        self,
        source_node: str,
        destination_node: str,
        channel: RingChannel = "req",
    ) -> bool:
        self._validate_route(source_node, destination_node, channel)
        direction = self._direction(source_node, destination_node)
        link = self._links[(channel, direction)][
            self._outgoing_link(source_node)
        ]
        return len(link) < self.config.link_slots_per_direction

    def record_injection_backpressure(
        self,
        partid: int,
        delay_ns: float,
        channel: RingChannel = "req",
        direction: RingDirection | None = None,
        source_node: str = "",
    ) -> None:
        for counters in (
            self._interval,
            self._per_partid[partid],
        ):
            counters["injection_backpressure_events"] += 1
            counters["injection_backpressure_ns"] += delay_ns
        if direction is not None:
            counters = self._per_channel_direction[
                (channel, direction)
            ]
            counters["injection_backpressure_events"] += 1
            counters["injection_backpressure_ns"] += delay_ns
            partid_counters = self._per_partid_channel_direction[
                (partid, channel, direction)
            ]
            partid_counters["injection_backpressure_events"] += 1
            partid_counters["injection_backpressure_ns"] += delay_ns
        if source_node:
            node_counters = self._per_node[source_node]
            node_counters["injection_backpressure_events"] += 1
            node_counters["injection_backpressure_ns"] += delay_ns

    def receive(
        self,
        request: Request,
        downstream: EndpointPort | Callable[[Request], None],
    ) -> bool:
        return self.transmit(
            request,
            "req",
            downstream,
            source_node=request.source_attach_node,
            destination_node=request.destination_node,
        )

    def transmit(
        self,
        request: Request,
        channel: RingChannel,
        downstream: EndpointPort | Callable[[Request], None],
        *,
        source_node: str,
        destination_node: str,
    ) -> bool:
        self._validate_route(source_node, destination_node, channel)
        direction = self._direction(source_node, destination_node)
        flit_count = (
            max(
                1,
                math.ceil(
                    request.size_bytes / self.config.flit_bytes
                ),
            )
            if channel == "dat"
            else 1
        )
        for counters in (
            self._interval,
            self._per_partid[request.partid],
            self._per_channel_direction[(channel, direction)],
            self._per_partid_channel_direction[
                (request.partid, channel, direction)
            ],
        ):
            counters["offered_flits"] += flit_count
        self._per_node[source_node]["offered_flits"] += flit_count
        if not self.can_inject(
            source_node,
            destination_node,
            channel,
        ):
            self.record_injection_backpressure(
                request.partid,
                self.hop_delay_ns,
                channel,
                direction,
                source_node,
            )
            return False

        self._transfer_sequence += 1
        transfer = TransferState(
            transfer_id=self._transfer_sequence,
            transaction=request,
            channel=channel,
            direction=direction,
            source_node=source_node,
            destination_node=destination_node,
            endpoint=self._normalize_endpoint(downstream),
            flit_count=flit_count,
            created_time_ns=self.kernel.now_ns,
        )
        for flit_index in range(flit_count):
            transfer.pending_flits.append(
                RingFlit(
                    transfer_id=transfer.transfer_id,
                    transaction=request,
                    channel=channel,
                    direction=direction,
                    source_node=source_node,
                    destination_node=destination_node,
                    flit_index=flit_index,
                    flit_count=flit_count,
                    injected_time_ns=self.kernel.now_ns,
                )
            )
        self._transfers[transfer.transfer_id] = transfer
        self._pending_transfer_ids.append(transfer.transfer_id)
        self._inject_pending()
        self._ensure_tick()
        return True

    def _validate_route(
        self,
        source_node: str,
        destination_node: str,
        channel: str,
    ) -> None:
        if channel not in self.CHANNELS:
            raise ValueError(f"Unsupported ring channel: {channel}")
        if source_node not in self.node_index:
            raise ValueError(f"Unknown ring source node: {source_node}")
        if destination_node not in self.node_index:
            raise ValueError(
                f"Unknown ring destination node: {destination_node}"
            )
        if source_node == destination_node:
            raise ValueError(
                "Ring transfer source and destination must differ"
            )

    def _inject_pending(self) -> None:
        pending_count = len(self._pending_transfer_ids)
        for _ in range(pending_count):
            transfer_id = self._pending_transfer_ids.popleft()
            transfer = self._transfers.get(transfer_id)
            if transfer is None or not transfer.pending_flits:
                continue
            link = self._links[
                (transfer.channel, transfer.direction)
            ][self._outgoing_link(transfer.source_node)]
            link_index = self._outgoing_link(
                transfer.source_node
            )
            while (
                transfer.pending_flits
                and len(link)
                < self.config.link_slots_per_direction
            ):
                flit = transfer.pending_flits.popleft()
                flit.injected_time_ns = self.kernel.now_ns
                link.append(flit)
                for counters in (
                    self._interval,
                    self._per_partid[flit.transaction.partid],
                    self._per_channel_direction[
                        (flit.channel, flit.direction)
                    ],
                    self._per_partid_channel_direction[
                        (
                            flit.transaction.partid,
                            flit.channel,
                            flit.direction,
                        )
                    ],
                    self._per_link[
                        (
                            flit.channel,
                            flit.direction,
                            link_index,
                        )
                    ],
                ):
                    counters["injected_flits"] += 1
                self._per_node[
                    flit.source_node
                ]["injected_flits"] += 1
            if transfer.pending_flits:
                self._pending_transfer_ids.append(transfer_id)
        self._sample_slots()

    def _ensure_tick(self) -> None:
        if self._tick_scheduled or not self._transfers:
            return
        self._tick_scheduled = True
        self.kernel.schedule(
            self.hop_delay_ns,
            self._tick,
            "ring-hop",
        )

    def _arrival_node(
        self,
        link_index: int,
        direction: RingDirection,
    ) -> int:
        if direction == "cw":
            return (link_index + 1) % len(self.node_order)
        return (link_index - 1) % len(self.node_order)

    def _tick(self) -> None:
        self._tick_scheduled = False
        completed_transfers: List[TransferState] = []
        next_links: Dict[
            Tuple[RingChannel, RingDirection],
            List[List[RingFlit]],
        ] = {
            key: [[] for _ in self.node_order]
            for key in self._links
        }
        for key in sorted(self._links):
            _, direction = key
            for link_index, link in enumerate(self._links[key]):
                arrival_index = self._arrival_node(
                    link_index,
                    direction,
                )
                arrival_node = self.node_order[arrival_index]
                for flit in link:
                    flit.hops += 1
                    for counters in (
                        self._interval,
                        self._per_partid[flit.transaction.partid],
                        self._per_channel_direction[key],
                        self._per_partid_channel_direction[
                            (
                                flit.transaction.partid,
                                flit.channel,
                                flit.direction,
                            )
                        ],
                        self._per_link[
                            (
                                flit.channel,
                                flit.direction,
                                link_index,
                            )
                        ],
                    ):
                        counters["hops"] += 1
                    transfer = self._transfers[flit.transfer_id]
                    if arrival_node == flit.destination_node:
                        if transfer.endpoint.can_accept(
                            flit.transaction
                        ):
                            completed = self._eject(flit, transfer)
                            if completed is not None:
                                completed_transfers.append(completed)
                            continue
                        flit.failed_ejections += 1
                        for counters in (
                            self._interval,
                            self._per_partid[
                                flit.transaction.partid
                            ],
                            self._per_channel_direction[key],
                            self._per_partid_channel_direction[
                                (
                                    flit.transaction.partid,
                                    flit.channel,
                                    flit.direction,
                                )
                            ],
                            self._per_link[
                                (
                                    flit.channel,
                                    flit.direction,
                                    link_index,
                                )
                            ],
                        ):
                            counters["failed_ejections"] += 1
                        self._per_node[
                            arrival_node
                        ]["failed_ejections"] += 1
                    if flit.hops % len(self.node_order) == 0:
                        flit.full_laps += 1
                        for counters in (
                            self._interval,
                            self._per_partid[
                                flit.transaction.partid
                            ],
                            self._per_channel_direction[key],
                            self._per_partid_channel_direction[
                                (
                                    flit.transaction.partid,
                                    flit.channel,
                                    flit.direction,
                                )
                            ],
                            self._per_link[
                                (
                                    flit.channel,
                                    flit.direction,
                                    link_index,
                                )
                            ],
                        ):
                            counters["full_laps"] += 1
                    next_links[key][arrival_index].append(flit)
        self._links = next_links
        for transfer in completed_transfers:
            transfer.endpoint.accept(transfer.transaction)
        self._inject_pending()
        self._sample_slots()
        if self._transfers:
            self._ensure_tick()

    def _eject(
        self,
        flit: RingFlit,
        transfer: TransferState,
    ) -> TransferState | None:
        transfer.ejected_flits += 1
        key = (flit.channel, flit.direction)
        for counters in (
            self._interval,
            self._per_partid[flit.transaction.partid],
            self._per_channel_direction[key],
            self._per_partid_channel_direction[
                (
                    flit.transaction.partid,
                    flit.channel,
                    flit.direction,
                )
            ],
        ):
            counters["ejected_flits"] += 1
        self._per_node[
            flit.destination_node
        ]["ejected_flits"] += 1
        if transfer.ejected_flits < transfer.flit_count:
            return None
        elapsed = max(
            0.0,
            self.kernel.now_ns - transfer.created_time_ns,
        )
        if transfer.channel == "req":
            transfer.transaction.timing.req_ring_delay_ns += elapsed
        else:
            transfer.transaction.timing.rsp_dat_ring_delay_ns += elapsed
        for counters in (
            self._interval,
            self._per_partid[flit.transaction.partid],
            self._per_channel_direction[key],
            self._per_partid_channel_direction[
                (
                    flit.transaction.partid,
                    flit.channel,
                    flit.direction,
                )
            ],
        ):
            counters["completed_transfers"] += 1
        del self._transfers[transfer.transfer_id]
        return transfer

    def _sample_slots(self) -> None:
        occupied = self.in_flight_flits
        self._slot_sample_sum += occupied
        self._slot_samples += 1
        self._in_flight_peak = max(self._in_flight_peak, occupied)

    def monitor_snapshot(self, interval_ns: float):
        average_occupancy = (
            self._slot_sample_sum / max(1, self._slot_samples)
        )
        row = {
            "msc_id": self.component_id,
            "msc_type": "noc",
            "model": "three_bidirectional_bufferless_rings",
            "node_order": list(self.node_order),
            "clock_mhz": self.config.clock_mhz,
            "flit_bytes": self.config.flit_bytes,
            "link_slots_per_direction": (
                self.config.link_slots_per_direction
            ),
            "hop_latency_cycles": self.config.hop_latency_cycles,
            "hop_delay_ns": self.hop_delay_ns,
            "tie_direction": self.config.tie_direction,
            "total_slots": self.total_slots,
            "slot_occupancy": average_occupancy,
            "queue_occupancy": average_occupancy,
            "in_flight_flits": self.in_flight_flits,
            "in_flight_peak": self._in_flight_peak,
            "source_pending_flits": sum(
                len(transfer.pending_flits)
                for transfer in self._transfers.values()
            ),
            "utilization": min(
                1.0,
                average_occupancy / max(1, self.total_slots),
            ),
            "requests": self._interval["completed_transfers"],
            "bytes": (
                self._interval["injected_flits"]
                * self.config.flit_bytes
            ),
            **self._interval,
            "per_channel_direction": {
                f"{channel}:{direction}": dict(
                    self._per_channel_direction[
                        (channel, direction)
                    ]
                )
                for channel in self.CHANNELS
                for direction in self.DIRECTIONS
            },
            "per_partid_channel_direction": {
                f"{partid}:{channel}:{direction}": dict(counters)
                for (partid, channel, direction), counters
                in sorted(
                    self._per_partid_channel_direction.items()
                )
            },
            "per_link": {
                f"{channel}:{direction}:link{link_index}": {
                    "source_node": self.node_order[link_index],
                    **dict(counters),
                }
                for (channel, direction, link_index), counters
                in sorted(self._per_link.items())
            },
            "per_node": {
                node_id: dict(self._per_node[node_id])
                for node_id in self.node_order
            },
            "per_partid": {
                str(partid): dict(values)
                for partid, values in self._per_partid.items()
            },
        }
        self._interval = _ring_counters()
        self._per_partid.clear()
        self._per_channel_direction.clear()
        self._per_partid_channel_direction.clear()
        self._per_link.clear()
        self._per_node.clear()
        self._slot_sample_sum = 0
        self._slot_samples = 0
        self._in_flight_peak = self.in_flight_flits
        return self.build_monitor_snapshot(
            self.kernel.now_ns,
            interval_ns,
            row,
        )
