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
actual_cache_occupancy_partid / allowed_cache_capacity_partid
```

For bandwidth:

```text
actual_bandwidth_partid / bw_max_partid
```

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

### Policy Stability

Track:

- Number of control updates per interval.
- Direction changes of bandwidth caps.
- Priority flapping.
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
| Priority latency improvement | measurable reduction under contention |
| Cache partition conformance | no PARTID exceeds allowed way/portion mask in exact mode |
| Monitor report interval jitter | deterministic under fixed seed |
| No-control vs controlled delta | visible in at least noisy-neighbor scenario |
