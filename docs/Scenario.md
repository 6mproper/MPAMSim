# Scenario Library

## 1. Scenario Definition Format

Each scenario is a YAML file containing:

```yaml
name: noisy_neighbor_basic
soc_profile: baseline_soc
workloads:
  - name: latency_service
    type: pointer_chase
    partid: 1
    pmg: 0
    requester_set: cpu0
    target_p99_ns: 500
  - name: bandwidth_hog
    type: stream_read
    partid: 2
    pmg: 0
    requester_set: cpu1-15
    injection_rate_gbps: 200
policies:
  - no_control
  - static_mpam
  - closed_loop_qos
```

## 2. Required Scenarios

### 2.1 Noisy Neighbor

Purpose:

Verify whether one high-bandwidth workload can damage another latency-sensitive workload.

Workloads:

- PARTID 1: latency-sensitive pointer chase.
- PARTID 2: streaming read/write bandwidth hog.

Metrics:

- PARTID 1 p99 latency.
- PARTID 2 bandwidth.
- Memory-controller queue occupancy.

Expected result:

- No-control baseline has high tail latency.
- Static MPAM reduces interference.
- Closed-loop control further improves p99 while keeping bandwidth utilization reasonable.

### 2.2 Core Scaling vs Shared L3

Purpose:

Evaluate how many cores should share one L3/SLC instance.

Sweep:

```text
cores_per_l3 = 4, 8, 16, 32
```

Metrics:

- Cache hit rate.
- Cache occupancy per PARTID.
- Tail latency.
- Memory bandwidth pressure.

Expected result:

More cores per L3 increases contention unless cache partitions and bandwidth control are adjusted.

### 2.3 Memory Controller Scaling

Purpose:

Evaluate number of memory controllers needed for isolation and bandwidth.

Sweep:

```text
num_memory_controllers = 1, 2, 4, 8
```

Metrics:

- Per-controller utilization.
- Queueing delay.
- Aggregate bandwidth.
- PARTID fairness.

Expected result:

More controllers reduce back-end queueing until NoC or cache becomes bottleneck.

### 2.4 LLM Inference: Prefill vs Decode

Purpose:

Model two-phase inference behavior.

Workloads:

- Prefill: high compute + bursty memory traffic.
- Decode: latency-sensitive small-batch traffic.
- Optional: KV cache traffic.

Metrics:

- Decode p99/p999 latency.
- Prefill throughput.
- Memory bandwidth burst behavior.

Expected result:

Static bandwidth cap may protect decode but reduce prefill throughput. Dynamic policy can relax cap when decode pressure is low.

### 2.5 LLM Training: Communication and Computation Overlap

Purpose:

Model overlap between compute traffic and communication traffic.

Workloads:

- Compute stream: activation/weight memory traffic.
- Communication stream: all-gather or reduce-scatter-like memory/DMA traffic.

Metrics:

- Overlap efficiency.
- Memory bandwidth contention.
- Tail latency of critical compute requests.

Expected result:

Flow control should shape communication bursts to avoid starving compute-critical accesses.

### 2.6 Power Cap

Purpose:

Validate whether traffic shaping can keep estimated power below cap.

Inputs:

- Power cap in watts.
- Per-byte DDR energy coefficient.
- Per-byte NoC energy coefficient.
- Cache access energy coefficient.

Metrics:

- Estimated power over time.
- Cap violation duration.
- QoS degradation.
- Bandwidth loss.

Expected result:

Background traffic is throttled first; latency-critical traffic receives minimum guaranteed resources.

## 3. Scenario Sweep Parameters

The scenario runner must support sweeps:

```yaml
sweep:
  cores_per_l3: [4, 8, 16]
  num_memory_controllers: [1, 2, 4]
  policy: [no_control, static_mpam, closed_loop_qos]
```

## 4. Scenario Output Naming

Recommended format:

```text
outputs/{scenario_name}/{timestamp}/{config_hash}/
├── run_summary.json
├── metrics.csv
├── per_partid_latency.csv
├── per_msc_utilization.csv
└── control_trace.csv
```
