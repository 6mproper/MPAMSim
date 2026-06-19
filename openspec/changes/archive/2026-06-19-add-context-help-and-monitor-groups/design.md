## Context

Every request already carries PARTID and PMG, but L3 and memory-controller interval counters are keyed only by PARTID. The web console polls those snapshots at each control interval and can therefore expose PMG-scoped values without introducing a new transport. The UI also has dense tables and abbreviated terms that need explanations without permanently consuming screen space.

## Goals / Non-Goals

**Goals:**

- Make configuration semantics discoverable through pointer hover and keyboard focus.
- Explain the behavioral differences among stream, pointer chase, random read, mixed read/write, and burst traffic.
- Expose live `(PARTID, PMG)` monitor-group data at the same interval cadence as existing charts.
- Show normalized L3 occupancy and MC bandwidth utilization percentages.
- Keep monitoring attribution separate from resource control.

**Non-Goals:**

- Implement architected monitor-selection registers, capture, NRDY, overflow, or interrupts.
- Apply CMIN, CMAX, CPBM, BMIN, or BMAX independently per PMG.
- Provide exact full-cache PMG occupancy or detailed DRAM command utilization.

## Decisions

### PMG-aware sampled cache metadata

Add `owner_pmg` to sampled ways. Allocation records the allocating request's PMG. A later hit from another PMG does not transfer ownership, matching allocation-oriented occupancy attribution. Cache interval traffic counters are keyed by `(PARTID, PMG)`.

### L3 occupancy utilization

For each monitor group:

```text
occupancy_rate = estimated_group_occupancy_bytes / PARTID_allowed_capacity_bytes
```

The rate is clamped to 100 percent. It is explicitly an eight-set sampled estimate, not exact CSU.

### PMG-aware memory-controller counters

Maintain additional interval counters keyed by `(PARTID, PMG)` while retaining PARTID-keyed enforcement and policy counters. Group bandwidth utilization is:

```text
group_bandwidth_gbps / memory_controller_total_bandwidth_gbps
```

The UI aggregates numerator and capacity across MC instances before calculating the displayed rate.

### Contextual help

Use one lightweight custom tooltip driven by `data-help`. It appears on hover and focus, supports dynamic controls, and avoids persistent explanatory panels. Native option titles are also emitted for select choices when useful.

### Live table

Add a `监控组` result tab. Rows are derived from configured 16-thread stimuli so idle groups remain visible, then merged with the latest L3 and MC snapshots. Percentage cells use compact progress bars for scanning.

## Risks / Trade-offs

- [Same PARTID and PMG can be used by multiple requesters] -> Display requester lists and aggregate by the architected monitor key.
- [Sampled PMG occupancy is noisy] -> Label it estimated and show bytes alongside percentage.
- [Many help targets can become distracting] -> Show tooltips only after hover/focus and keep them short.
- [Nested select options have inconsistent browser hover behavior] -> Put the full type comparison on the Type control and individual descriptions in option titles.
