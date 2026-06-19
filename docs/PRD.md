# PRD: SoC Flow Control / MPAM System Simulation Platform

## 1. Problem Definition

Modern SoCs contain many requesters competing for shared memory-system resources: shared L3/SLC cache, NoC links, NoC queues, DDR/HBM channels, memory-controller scheduler entries, reorder buffers, write buffers, and rate adapters. Without explicit control, high-bandwidth or bursty agents can degrade latency-sensitive workloads, violate QoS/SLA constraints, and trigger power or thermal caps.

MPAM provides an architectural framework for resource partitioning and monitoring. However, MPAM itself is not a complete system-level flow-control loop. A practical SoC needs:

- Identification: request tagging and attribution.
- Enforcement: per-resource arbitration, throttling, shaping, and partitioning.
- Monitoring: per-tenant and per-resource counters.
- Control policy: static or dynamic adjustment based on target KPIs.
- System integration: OS/hypervisor/runtime mapping to hardware knobs.

This project builds a configurable simulation platform to evaluate these mechanisms before RTL or silicon availability.

## 2. Target Users

- SoC architects validating NoC, cache, and memory QoS mechanisms.
- MPAM architects validating PARTID/PMG resource-control mapping.
- Firmware/software architects evaluating runtime control policies.
- Performance engineers analyzing noisy-neighbor, LLM inference, training, and power-cap scenarios.
- Verification engineers creating early architecture-level test scenarios.

## 3. Main Objectives

### Objective 1: Configurable SoC Topology

The simulator shall allow users to define:

- Number of CPU clusters.
- Number of cores per cluster.
- Number of hardware threads per core.
- Number of accelerators and DMA engines.
- L1/L2/L3/SLC hierarchy.
- How many cores share one L3 or SLC.
- Number of memory controllers.
- Number of DDR/HBM channels per memory controller.
- NoC topology and link bandwidth.
- Queue depths and buffer sizes.

This is mandatory because MPAM resource controls are implemented in memory-system components, and topology determines where controls can be applied.

### Objective 2: MPAM-like Partitioning and Monitoring

The simulator shall support:

- PARTID tagging.
- PMG sub-attribution.
- Per-MSC settings table.
- Cache portion partitioning.
- Memory bandwidth max/min model.
- Priority control model.
- Resource usage monitors.
- Per-PARTID and per-PMG statistics.

### Objective 3: New Flow-Control Policy Exploration

The simulator shall support multiple policies:

- No-control baseline.
- Static MPAM partitioning.
- Static bandwidth cap.
- Static priority/QoS class.
- Credit/backpressure control.
- Dynamic closed-loop controller.
- Power-cap aware flow control.

### Objective 4: Scenario Library

The simulator shall include scenarios for:

- Noisy neighbor.
- Latency-sensitive service vs bandwidth hog.
- LLM inference prefill/decode contention.
- LLM training communication/computation overlap.
- DMA/PCIe/accelerator memory interference.
- Power capping.
- Mixed-criticality workloads.

## 4. Functional Requirements

### FR-1: User Control Interface

The simulator shall expose a user-facing control interface through YAML or JSON configuration files.

The first version does not require a GUI. A CLI plus configuration file is sufficient.

Required top-level configuration sections:

```yaml
soc:
  clusters: []
  caches: []
  noc: {}
  memory: {}

mpam:
  partid_width: 8
  pmg_width: 8
  partitions: []
  msc_controls: []

workloads: []
policies: []
simulation: {}
outputs: {}
```

### FR-2: Topology Definition

The configuration must define:

- `num_clusters`
- `cores_per_cluster`
- `threads_per_core`
- `l3_instances`
- `cores_per_l3`
- `l3_size_bytes`
- `l3_ways`
- `num_memory_controllers`
- `channels_per_memory_controller`
- `memory_bandwidth_gbps_per_channel`
- `noc_topology`
- `noc_link_bandwidth_gbps`
- `queue_depths`

These parameters must be explicit, not hard-coded.

### FR-3: Workload Definition

Each workload shall define:

- Requester type: CPU thread, VM, process, accelerator, DMA, PCIe device.
- PARTID.
- PMG.
- Access type: read, write, mixed.
- Address distribution.
- Request size.
- Injection rate.
- Burstiness.
- Latency sensitivity.
- SLA target.

### FR-4: MPAM Enforcement

Each MSC shall implement a settings table indexed by PARTID. Initial controls:

- Cache portion bitmask.
- Bandwidth maximum.
- Bandwidth minimum or reserved bandwidth approximation.
- Priority class.
- Monitor enable/disable.

### FR-5: Monitoring

The simulator shall collect:

- Per-PARTID request count.
- Per-PARTID bytes transferred.
- Per-PARTID average latency.
- Per-PARTID p95/p99/p999 latency.
- Per-PARTID cache occupancy.
- Per-PARTID cache hit/miss count.
- Per-MSC queue occupancy.
- Per-memory-controller bandwidth.
- Stall cycles/time due to throttling.
- Dropped or delayed requests, if modeled.

### FR-6: Policy Plug-in Interface

Policies shall be implemented as plug-ins with the following interface:

```python
class Policy:
    def on_init(self, topology, mpam_config): ...
    def on_interval(self, time_ns, monitors): ...
    def update_controls(self) -> list[ControlUpdate]: ...
```

### FR-7: Output

The simulator shall output:

- `run_summary.json`
- `metrics.csv`
- `per_partid_latency.csv`
- `per_msc_utilization.csv`
- `control_trace.csv`
- Optional timeline trace.

## 5. Non-functional Requirements

### NFR-1: Repeatability

All scenarios must be reproducible using seed values.

### NFR-2: Extensibility

New MSC types, policies, workload generators, and metrics must be addable without rewriting the simulation core.

### NFR-3: Debuggability

Every request must carry a request ID, requester ID, PARTID, PMG, address, size, and timestamp.

### NFR-4: Performance

Version 1 should simulate at least 1 million abstract requests within a few minutes on a developer laptop.

### NFR-5: Traceability

All major modeling assumptions shall be captured in `docs/Model_Assumptions.md` when implemented.

## 6. Acceptance Criteria

The project is accepted when:

1. A baseline topology can be loaded from YAML.
2. At least 16 CPU cores, 4 clusters, 2 shared L3/SLC instances, and 2 memory controllers can be modeled.
3. At least 4 PARTIDs can run concurrently.
4. Cache partitioning changes hit rate and occupancy in expected directions.
5. Bandwidth caps limit per-PARTID bandwidth.
6. Priority control changes latency distribution.
7. Monitors report per-PARTID/per-MSC counters.
8. At least 5 scenarios run through CLI and generate CSV/JSON output.
9. Regression tests verify basic correctness.
