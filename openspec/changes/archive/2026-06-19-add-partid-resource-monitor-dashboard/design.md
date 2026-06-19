# Design: PARTID Resource Monitor Dashboard

## Data Model

Each requester runtime maintains per-PARTID counters:

- current outstanding requests;
- peak outstanding requests observed during the control interval;
- cumulative issued and completed requests;
- cumulative requester-side backpressure;
- configured requester outstanding capacity.

The collector emits one CPU monitor row per requester/PARTID/control interval. Multiple requesters using the same PARTID are aggregated in the UI by summing outstanding values and capacities.

## Resource Views

The dashboard has a shared PARTID selector and three resource modes:

- CPU: requester mapping, current/peak OSTD, OSTD utilization, issued/completed counts, and source backpressure.
- L3: estimated occupancy and utilization, sampled access bandwidth, hit rate, allocation denials, CMIN, CMAX, and CPBM.
- MC: achieved bandwidth and controller utilization, requests, average queue delay, throttle delay, BMIN, BMAX, limit mode, priority, and limit events.

L3 occupancy remains an eight-set sampled estimate. MC bandwidth is calculated over the control interval. CPU OSTD is an interval-boundary gauge with a peak recorded between boundaries.

## Selection

The console exposes one toggle for every PARTID 0 through 15. Selection is independent and persistent while the page is open. Select-all and clear commands are provided. At least one empty-state message is shown when no PARTID is selected.

The same selection filters:

- the active CPU/L3/MC resource table;
- P99 and bandwidth trend series;
- existing per-PARTID and MPAM aggregate tables.

## Feedback State

For each PARTID, the dashboard derives a concise feedback state:

- `disabled` for no-control policy;
- `static` for static MPAM policy;
- `monitoring` for closed-loop policy without an update at or before the selected time;
- `adjusted` when the closed loop has applied an update.

The row also exposes the latest update time, target, field, and reason when available. Effective L3 and MC controls are taken from the latest MSC snapshots, so displayed values reflect runtime updates rather than only the initial form.

## Compatibility

Existing API fields and result views remain available. The interactive API adds a top-level `cpu` row list. Export adds `per_cpu_partid.csv`.
