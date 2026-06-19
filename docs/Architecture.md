# Architecture Design: SoC Flow Control / MPAM Simulator

## 1. Architectural Principle

The simulator is organized around the same control chain used in real SoC flow control:

```text
Workload / Tenant / VM / Thread
        ↓
Requester / PE / DMA / Accelerator
        ↓ carries PARTID / PMG / QoS / Stream ID
NoC / Cache / SLC / Memory Controller MSCs
        ↓
Resource monitors and counters
        ↓
Policy controller
        ↓
Resource-control updates
```

The system must separate:

- User interface and visualization.
- Topology model.
- Traffic model.
- Resource model.
- MPAM model.
- Flow-control policy.
- Monitoring and reporting.

## 2. Module Decomposition

### 2.0 User Interface and Visualization Layer

Responsibilities:

- Expose YAML/JSON, CLI, and Python APIs.
- Validate user stimulus and topology before simulation.
- Generate visualization-ready data and static HTML reports.
- Keep reporting separate from simulation semantics.

Suggested files:

```text
src/cli/run.py
src/cli/run_sweep.py
src/monitor/report.py
src/monitor/plots.py
```

### 2.1 Simulation Kernel

Responsibilities:

- Discrete-event scheduler.
- Global time management.
- Event queue.
- Component registration.
- Deterministic random seed support.

Suggested files:

```text
src/sim/event.py
src/sim/kernel.py
src/sim/component.py
```

### 2.2 Configuration Layer

Responsibilities:

- Load YAML/JSON config.
- Validate topology and MPAM settings.
- Instantiate components.

Suggested files:

```text
src/config/schema.py
src/config/loader.py
src/config/validator.py
```

### 2.3 Traffic Layer

Responsibilities:

- Materialize requesters from cores, threads, accelerators, DMA, PCIe, or synthetic tenants.
- Generate requests.
- Attach metadata: requester ID, PARTID, PMG, address, size, read/write, QoS class.
- Model burstiness and arrival processes.

Suggested files:

```text
src/traffic/generator.py
src/traffic/requester.py
src/traffic/request.py
src/traffic/workload.py
```

### 2.4 MPAM Layer

Responsibilities:

- Store PARTID/PMG metadata.
- Implement per-MSC settings table.
- Apply cache and bandwidth controls.
- Collect monitoring counters.
- Provide control update API.

Suggested files:

```text
src/mpam/partid.py
src/mpam/settings.py
src/mpam/control.py
src/mpam/monitor.py
```

### 2.5 Cache MSC

Responsibilities:

- Abstract cache with sets/ways or coarse capacity approximation.
- Cache portion partitioning.
- Per-PARTID occupancy and hit/miss accounting.
- Optional cache capacity partitioning approximation.

Suggested files:

```text
src/cache/cache_msc.py
src/cache/replacement.py
src/cache/partition.py
```

### 2.6 NoC MSC

Responsibilities:

- Route requests from requesters to cache/memory.
- Model links, routers, queues, virtual channels.
- Support queueing delay and arbitration.
- Support priority and credit/backpressure policies.

Suggested files:

```text
src/noc/router.py
src/noc/link.py
src/noc/queue.py
src/noc/topology.py
src/noc/flow_control.py
```

### 2.7 Memory Controller MSC

Responsibilities:

- Model memory-controller queues.
- Model channel bandwidth and service time.
- Enforce per-PARTID bandwidth caps.
- Map priorities to scheduling classes.
- Record bandwidth and latency metrics.

Suggested files:

```text
src/ddr/memctrl.py
src/ddr/channel.py
src/ddr/scheduler.py
```

### 2.8 Policy Layer

Responsibilities:

- Implement flow-control strategies.
- Read monitor snapshots.
- Generate control updates.

Suggested files:

```text
src/scheduler/policy_base.py
src/scheduler/no_control.py
src/scheduler/static_mpam.py
src/scheduler/bandwidth_cap.py
src/scheduler/priority_policy.py
src/scheduler/closed_loop.py
src/scheduler/powercap_policy.py
```

### 2.9 Monitor and Reporting Layer

Responsibilities:

- Aggregate per-request and per-component metrics.
- Compute percentiles.
- Export JSON and CSV.
- Export timeline traces, topology graph data, and static HTML reports.

Suggested files:

```text
src/monitor/metrics.py
src/monitor/collector.py
src/monitor/exporter.py
src/monitor/report.py
src/monitor/plots.py
```

## 3. Core Runtime Flow

```text
1. Load config.
2. Validate topology.
3. Build requesters and stimulus generators.
4. Build SoC components.
5. Build MPAM settings tables.
6. Build workloads.
7. Register policies.
8. Run discrete-event loop.
9. On every control interval:
   9.1 collect monitor snapshot
   9.2 policy computes updates
   9.3 apply updates to MSC settings tables
10. Stop at simulation end time.
11. Export metrics, traces, topology data, and optional report.
```

## 4. Key Classes

```python
@dataclass
class Request:
    request_id: int
    requester_id: str
    partid: int
    pmg: int
    addr: int
    size_bytes: int
    op: str
    issue_time_ns: int
    qos_class: int = 0
    priority: int = 0

@dataclass
class MPAMSetting:
    partid: int
    cache_portion_bitmap: str | None
    bw_max_gbps: float | None
    bw_min_gbps: float | None
    priority: int | None

@dataclass
class MonitorSnapshot:
    time_ns: int
    per_partid: dict
    per_msc: dict
```

## 5. Hardware Topology Modeling Requirements

The following items must be first-class user configuration parameters:

- Number of CPU clusters.
- Number of cores per cluster.
- Number of hardware threads per core.
- Mapping from core to L3/SLC.
- Number of L3/SLC instances.
- L3/SLC size, ways, line size.
- Number of memory controllers.
- Channels per memory controller.
- Memory bandwidth per channel.
- NoC topology and link bandwidth.
- NoC queue and VC configuration.
- Requester-to-NoC attachment points.

Do not derive these implicitly unless defaults are explicitly documented.

## 6. Why User Control Interface Must Include Hardware Knobs

The simulator is used for architecture exploration. If topology is fixed in code, it cannot answer the central design questions:

- How many cores should share one L3?
- How many memory controllers are needed for target isolation?
- Where should MPAM monitors be placed?
- Whether control at cache, NoC, memory controller, or all three is necessary?
- What happens when thread count increases but memory-controller count stays fixed?
- How much control granularity is needed per PARTID?

Therefore, topology must be visible at the user interface layer.
