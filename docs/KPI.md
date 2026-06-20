# KPI and Metrics Definition

## 1. System-Level KPIs

### Throughput

```text
throughput_gbps = completed_bytes * 8 / simulation_time_ns
```

Track:

- Total throughput.
- Per-PARTID throughput.
- Per-memory-controller throughput.
- Per-NoC-link throughput.

### Latency

Request latency:

```text
latency_ns = completion_time_ns - issue_time_ns
```

Track:

- Average latency.
- p50 latency.
- p95 latency.
- p99 latency.
- p999 latency.
- Max latency.

### Fairness

Jain fairness index:

```text
J = (sum(x_i)^2) / (n * sum(x_i^2))
```

Where `x_i` can be per-PARTID achieved bandwidth or normalized SLA satisfaction.

### Isolation

Suggested isolation metric:

```text
isolation_loss = latency_with_interference / latency_alone
```

Lower is better. A value near 1 means good isolation.

### Resource Utilization

Track:

- L3/SLC occupancy.
- Cache hit rate.
- NoC link utilization.
- NoC queue occupancy.
- Memory-controller utilization.
- DDR/HBM channel utilization.

## 2. MPAM-Specific KPIs

### Partition Conformance

```text
actual_resource_share / configured_resource_share
```

For cache:

```text
actual_cache_share_percent = estimated_occupancy / physical_cache_capacity
cmin_gap = max(0, configured_cmin_percent - actual_cache_share_percent)
cmax_overshoot = max(0, actual_cache_share_percent - effective_cmax_percent)
```

Evaluate `cmin_gap` only when the PARTID has demand and the L3 is contended.
Always interpret effective CMIN/CMAX after intersecting with CPBM reachability.

For bandwidth:

```text
actual_bandwidth_partid / bw_max_partid
```

Evaluate BMIN shortfall only when the PARTID has demand and the MC is
contended. Treat soft-BMAX borrowing without contention as work-conserving,
not as a cap failure. For hard BMAX, track both steady-state error and
short-window overshoot.

### MC QoS Effect

Track:

- configured/base QoS in `[0, 7]`;
- request-weighted effective QoS;
- BMIN-promoted requests;
- softlimit-demoted requests;
- aging promotion steps;
- same-demand throughput and queue-delay delta versus equal-QoS control.

### Monitor Accuracy

If golden counters are available:

```text
monitor_error = abs(model_counter - golden_counter) / golden_counter
```

### Control Effectiveness

```text
improvement = metric_baseline / metric_controlled
```

For latency, higher improvement is better. For throughput loss, lower loss is better.

## 3. Flow-Control KPIs

### Throttle Efficiency

```text
useful_throttle_ratio = latency_improvement / throughput_loss
```

### Queue Stabilization

Track queue occupancy over time. A good controller should reduce sustained queue buildup and avoid oscillation.

For deterministic case comparison, report both peak queue occupancy and queue
area:

```text
queue_area_entry_ns = sum(queue_occupancy_i * interval_ns_i)
```

Peak captures the worst instantaneous pressure. Queue area captures how much
pressure persists over time; lower is better when offered load and run length
are held constant.

For L3 admission, also track:

```text
l3_queue_delay_ns
l3_admission_backpressure_ns
l3_queue_full_events
l3_active_lookup_slots
```

Queue depth defines waiting capacity; lookup parallelism defines service
concurrency. Both are needed to interpret whether source OSTD is accumulating
at L3 or passing pressure downstream.

### Policy Stability

Track:

- Number of control updates per interval.
- Direction changes of bandwidth caps.
- MC QoS flapping.
- Over-correction events.

## 4. Power-Cap KPIs

### Cap Violation Ratio

```text
cap_violation_ratio = time_power_above_cap / total_time
```

### Cap Overshoot

```text
max_overshoot_w = max(power_w - cap_w)
```

### QoS Under Cap

```text
qos_degradation = p99_under_cap / p99_without_cap
```

## 5. Acceptance Thresholds for v1

Suggested default thresholds:

| KPI | Target |
|---|---|
| Bandwidth cap error | <= 10% in steady state |
| MC QoS latency improvement | measurable reduction under contention |
| Cache partition conformance | sampled ownership respects effective CMAX percentage within one-line tolerance |
| Monitor report interval jitter | deterministic under fixed seed |
| No-control vs controlled delta | visible in at least noisy-neighbor scenario |
