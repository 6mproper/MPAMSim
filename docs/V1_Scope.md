# V1 Scope: SoC Flow Control / MPAM Simulator

## 1. Goal

V1 must prove whether the simulator can explain and change shared-resource interference at SoC level.

Primary question:

```text
Given configurable requesters, topology, MPAM-style tags, MSC controls, and monitor feedback,
can we reproduce noisy-neighbor interference and show that bandwidth caps, priority, cache
partitioning, and credit/backpressure controls change latency, throughput, queueing, and occupancy
in the expected directions?
```

## 2. In Scope

- Abstract request generation from CPU threads, accelerators, DMA streams, or tenants.
- User-configurable stimulus through YAML/JSON and Python API.
- Visualization-ready results and a generated static report path.
- Request metadata: request ID, requester ID, PARTID, PMG, address, size, op, issue time, QoS class, priority.
- Configurable topology: clusters, cores, threads, SLC/L3 sharing, NoC, queues, virtual channels, memory controllers, channels, and schedulers.
- Multicore behavior at request-injection and shared-resource contention level.
- MPAM-style PARTID/PMG lookup and per-MSC settings tables.
- Cache/SLC capacity approximation with per-PARTID portion limits and occupancy/hit-rate counters.
- NoC fixed-hop latency, queueing delay, priority arbitration, and credit/backpressure hooks.
- Memory-controller token-bucket bandwidth cap, priority-aware scheduling, queue occupancy, and utilization.
- Monitors for per-PARTID, per-PMG, and per-MSC counters.
- Policies: no_control, static_mpam, bandwidth_cap, priority_policy, credit_flow_control, closed_loop_qos.
- Output traces sufficient for root-cause attribution.

## 3. Out of Scope for V1

- Cache coherency and cache-coherent transaction ordering.
- Cycle-accurate CPU pipeline, load/store queue, or prefetcher behavior.
- Full MPAM architectural register model.
- Full exception-level, security-state, virtualization, ACPI table, or Linux resctrl implementation.
- Detailed DRAM timing, row-buffer policy, refresh, bank conflicts, or PHY modeling.
- Exact cache replacement and exact way-mask model, except as a later optional mode.
- Full power-cap policy and LLM-specific scenario fidelity before baseline QoS mechanisms are validated.
- Live interactive GUI. V1 should emit visualization-ready files and may generate static HTML.

## 4. V1 Critical Path

```text
workload -> requester shaper -> NoC queue/arbitration -> SLC/cache approximation
         -> memory-controller queue/scheduler/token bucket -> completion
         -> monitors -> policy update -> MSC settings
```

The simulator should attribute latency into:

- `noc_delay_ns`
- `cache_delay_ns`
- `mem_queue_delay_ns`
- `mem_service_delay_ns`
- `throttle_delay_ns`
- `total_latency_ns`

## 5. V1 Acceptance Tests

V1 is useful only if these effects are measurable:

- Bandwidth cap reduces achieved bandwidth for the capped PARTID.
- Higher priority reduces protected PARTID tail latency under contention.
- Cache portion limit changes occupancy and hit-rate directionally.
- Credit/backpressure reduces sustained queue buildup.
- Closed-loop policy changes controls with hysteresis and does not flap every interval.
- Fixed seed produces deterministic output.
- Invalid topology or MPAM configuration fails validation.
