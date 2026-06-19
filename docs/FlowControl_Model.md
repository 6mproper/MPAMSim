# New Flow-Control Model Design

## 1. Flow-Control Objective

The new flow-control policy aims to improve system behavior beyond static MPAM settings.

Target properties:

- Preserve latency-sensitive workloads.
- Limit noisy-neighbor interference.
- Maintain fairness across tenants.
- Keep memory/NoC utilization high.
- Support power-cap or thermal-cap constraints.
- Avoid starvation.

## 2. Control Layers

### Layer 1: Requester-side shaping

Controls request injection from CPU, DMA, or accelerator.

Knobs:

- Injection rate cap.
- Burst length cap.
- Outstanding transaction cap.
- Per-stream credit limit.

### Layer 2: NoC queue and arbitration

Controls how traffic traverses interconnect.

Knobs:

- Virtual-channel allocation.
- Per-class arbitration weight.
- Queue admission threshold.
- Credit/backpressure threshold.
- Priority override.

### Layer 3: Cache/SLC allocation

Controls shared-cache occupancy and replacement.

Knobs:

- Cache way/portion mask.
- Replacement bias.
- Allocation throttle.

### Layer 4: Memory-controller scheduling

Controls DRAM/HBM access.

Knobs:

- Per-PARTID token bucket.
- Priority queue class.
- Read/write queue weight.
- Row-buffer locality bias.
- Channel selection.

### Layer 5: Closed-loop policy

Uses monitor data to adjust Layer 1-4 knobs.

## 3. Policies to Implement

### 3.1 NoControlPolicy

Baseline. No throttling, no partitioning, default scheduler.

### 3.2 StaticMPAMPolicy

Applies static cache masks, bandwidth caps, and priority values from config.

### 3.3 PriorityPolicy

Maps latency-sensitive PARTIDs to higher priority at NoC and memory controller.

### 3.4 CreditFlowControlPolicy

Maintains per-stream credits. A source can inject only when credits are available.

Parameters:

```yaml
credit_policy:
  initial_credit: 64
  refill_on_completion: true
  max_outstanding_per_partid: 128
  backpressure_threshold: 0.8
```

### 3.5 ClosedLoopQoSPolicy

Every control interval:

1. Read p99 latency and bandwidth per PARTID.
2. Compare with target SLA.
3. If p99 exceeds target, increase priority or reduce competing PARTID cap.
4. If bandwidth hog exceeds allowed budget, reduce token rate.
5. If utilization is low, relax caps.

Pseudo-code:

```python
for partid in monitored_partitions:
    if p99_latency[partid] > target_p99[partid]:
        raise_priority(partid)
        reduce_background_bw()
    if bandwidth[partid] > bw_budget[partid]:
        reduce_bw_max(partid)
    if total_memory_util < util_low_threshold:
        relax_caps()
```

### 3.6 PowerCapPolicy

Converts power cap into traffic cap.

Simplified model:

```text
estimated_power = static_power + k_noc * noc_bytes + k_ddr * ddr_bytes + k_cache * cache_accesses
```

If estimated power exceeds cap:

- First throttle background PARTIDs.
- Then reduce burst length.
- Then lower priority of non-critical streams.
- Preserve minimum reservation for latency-critical streams.

## 4. Required Monitors

Closed-loop control requires:

- p99 latency per PARTID.
- Bandwidth per PARTID.
- Queue occupancy per MSC.
- Cache miss rate per PARTID.
- Throttle delay per PARTID.
- Estimated power per interval.

## 5. Stability Requirements

The controller must avoid oscillation.

Recommended mechanisms:

- Control interval not shorter than memory-system response time.
- Hysteresis threshold.
- Minimum hold time after each control update.
- Step-limited change of caps and priorities.
- Saturation limits for all knobs.

Example:

```yaml
closed_loop:
  interval_ns: 100000
  p99_hysteresis: 0.1
  max_bw_step_percent: 10
  min_hold_intervals: 3
```

## 6. Evaluation Questions

The simulator should answer:

- Does static MPAM meet p99/p999 latency targets?
- How much bandwidth is lost due to over-throttling?
- Which resource is the real bottleneck: SLC, NoC, or memory controller?
- Does priority control reduce latency without starving background traffic?
- Does credit control reduce queue buildup?
- Can power cap be enforced with acceptable QoS loss?
