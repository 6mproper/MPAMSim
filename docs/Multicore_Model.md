# Multicore Behavior Model

## 1. Goal

V1 must model multicore behavior at the memory-system pressure level. It does not model CPU pipeline execution, instruction retirement, cache coherency, or ISA-level ordering. It models how many cores, threads, and agents inject requests into shared SoC resources.

## 2. Hierarchy

The multicore hierarchy is:

```text
cluster -> core -> hardware thread -> requester -> NoC attach node -> shared L3/SLC -> memory controller
```

Required relationships:

- Each core belongs to exactly one cluster.
- Each hardware thread belongs to exactly one core.
- Each requester has one NoC attachment point.
- Each core maps to one L3/SLC instance for V1.
- Multiple clusters may share the same L3/SLC.
- Memory address mapping selects a memory controller/channel.

## 3. Core/Thread Behavior

Each CPU thread requester has:

- Independent traffic generator.
- PARTID/PMG assignment.
- Optional QoS class.
- Maximum outstanding request count.
- Optional requester-side credit limit.
- Optional latency target.

Per-core aggregation should track:

- Active threads.
- Issued requests.
- Completed requests.
- Outstanding requests.
- Stall or backpressure time.

## 4. Shared-Resource Interference

V1 multicore interference is caused by:

- More requesters sharing one L3/SLC capacity pool.
- More requesters sharing NoC queues and links.
- More requesters sharing memory-controller scheduler entries and bandwidth.
- Background PARTIDs consuming tokens, queues, or cache capacity.

The simulator should not require a fixed core count. The same scenario must support sweeps over:

- `cores_per_cluster`
- `threads_per_core`
- active requester count
- `cores_per_l3`
- memory-controller count

## 5. Future SoC Interface

To leave room for complete SoC architecture, every requester should use a generic source-agent interface:

```python
class Requester:
    requester_id: str
    requester_type: str
    attach_node: str
    partid: int
    pmg: int
    qos_class: int
    max_outstanding: int

    def next_request(self, time_ns): ...
    def on_completion(self, request): ...
```

CPU cores, GPU blocks, NPU, ISP, DMA, PCIe, and synthetic tenants should plug into this same interface.
