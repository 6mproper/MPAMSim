## Why

The console exposes many architecture controls but currently requires users to infer their meaning, especially stimulus types and MPAM limit modes. It also aggregates most live observability by PARTID, so software cannot inspect PMG-scoped monitor groups or directly see L3 occupancy and memory bandwidth utilization percentages.

## What Changes

- Add hover and keyboard-focus explanations for configuration categories, fields, table columns, policy modes, result views, and stimulus options.
- Explain all stimulus workload types and rate units directly from the Type and Unit controls.
- Track L3 traffic and sampled ownership by `(PARTID, PMG)` monitor group.
- Track memory-controller service, bandwidth, delay, and limit events by `(PARTID, PMG)` monitor group.
- Add a live software-visible monitor-group table with requester mapping, L3 estimated occupancy/utilization, L3 sampled bandwidth, MC achieved bandwidth/utilization, requests, and bytes.
- Preserve PARTID as the resource-control key; PMG remains a monitoring and attribution key.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interactive-simulation-console`: Add contextual help and a live per-monitor-group result view.
- `mpam-l3-control`: Add PMG-scoped sampled L3 traffic and occupancy monitoring.
- `mpam-memory-bandwidth`: Add PMG-scoped bandwidth usage and utilization monitoring.

## Impact

- Extends cache and memory-controller monitor snapshots with `monitor_groups`.
- Adds tooltip behavior and a monitor-group table to the static web console.
- Updates monitor behavior documentation and regression tests.
- Does not change MPAM control-table indexing or claim architected feature-page/register behavior.
