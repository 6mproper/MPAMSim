# Stimulus Model

## 1. Goal

The stimulus model defines how users create traffic pressure on the SoC. It must be expressive enough to model multicore CPU traffic, accelerators, DMA, PCIe-like streams, latency-sensitive services, bandwidth hogs, and phase-based workloads, while remaining abstract enough for fast V1 simulation.

## 2. Requester Model

Every traffic source is a requester.

Required requester fields:

```yaml
requesters:
  - id: cpu0.t0
    type: cpu_thread
    cluster: cluster0
    core: cpu0
    thread: 0
    attach_node: r0
    max_outstanding: 32
  - id: dma0
    type: dma
    attach_node: r3
    max_outstanding: 128
```

Requester types:

- `cpu_thread`
- `cpu_core`
- `cpu_cluster`
- `accelerator`
- `dma`
- `pcie`
- `synthetic_tenant`

V1 may auto-expand cluster/core/thread requesters from `soc.clusters`, but the internal model must still materialize explicit requester IDs.

Auto-expansion form:

```yaml
requesters:
  auto_expand_cpu_threads: true
  defaults:
    max_outstanding: 32
  core_attach_nodes:
    cpu0: r0
    cpu1: r0
  explicit:
    - id: dma0
      type: dma
      attach_node: r3
      max_outstanding: 128
```

The resolved model must still contain concrete requester IDs such as `cpu0.t0`, `cpu0.t1`, and `dma0`.

## 3. Workload Model

Required workload fields:

```yaml
workloads:
  - name: latency_service
    type: pointer_chase
    requesters: [cpu0.t0]
    partid: 1
    pmg: 0
    request_size_bytes: 64
    read_ratio: 1.0
    injection:
      mode: poisson
      rate_mrps: 20
      scope: aggregate
      burst_length: 1
    address:
      distribution: random
      working_set_bytes: 67108864
      locality: low
    target_p99_ns: 500
```

Supported workload types:

- `stream`
- `pointer_chase`
- `random_read`
- `mixed_rw`
- `bursty_dma`
- `phase_based`
- `replay_trace` as a future extension.

### 3.1 Interactive 8-Core / 16-Thread Matrix

The local console uses a fixed reference topology of eight cores and two
hardware threads per core. It exposes 16 stimulus rows with the mapping:

```text
row 0  -> cpu0.t0
row 1  -> cpu0.t1
...
row 14 -> cpu7.t0
row 15 -> cpu7.t1
```

Every enabled row creates one independent workload and configures:

- PARTID and PMG.
- workload type.
- MRPS or Gbps injection rate.
- request size and read ratio.
- working-set size.
- optional P99 target.

Defaults map row N to PARTID N and PMG N. This is an experiment default, not
an architectural restriction: multiple rows may share one PARTID while using
different PMGs.

## 4. Injection Controls

Stimulus must expose the variables that flow control will act on:

- `rate_mrps` or `rate_gbps`
- `scope: aggregate | per_requester`
- `burst_length`
- `burst_period_ns`
- `max_outstanding`
- `think_time_ns`
- `start_ns`
- `stop_ns`
- `phase`
- `read_ratio`
- `request_size_bytes`

These are stimulus inputs. Flow-control policies may override effective injection through shaping or credit gates, but must record the difference as throttling or backpressure.

`aggregate` means the configured rate is divided among all requesters in the workload. `per_requester` means each requester injects at the configured rate, so activating more cores increases total offered load.

## 5. Phase-Based Stimulus

A workload may have phases:

```yaml
phases:
  - name: warmup
    start_ns: 0
    duration_ns: 1000000
    injection_rate_gbps: 20
  - name: burst
    start_ns: 1000000
    duration_ns: 200000
    injection_rate_gbps: 200
  - name: steady
    start_ns: 1200000
    duration_ns: 5000000
    injection_rate_gbps: 80
```

This keeps LLM prefill/decode, DMA bursts, and training communication patterns representable without implementing domain-specific models in V1.

## 6. Sweep Interface

Sweeps are first-class stimulus experiments:

```yaml
sweep:
  cores_active: [1, 4, 8, 16]
  background_rate_gbps: [50, 100, 200]
  mc_count: [1, 2, 4]
  policy: [no_control, static_mpam, closed_loop_qos]
```

The runner must stamp each run with the resolved config and a config hash.
