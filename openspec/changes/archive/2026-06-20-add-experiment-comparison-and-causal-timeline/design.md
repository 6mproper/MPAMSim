# Design: Experiment Comparison And Causal Timeline

## Four-Case Experiment

The experiment clones the submitted parameters four times and changes only enforcement switches and policy:

| Case | BMAX | CBusy | Other controls | Policy |
|---|---:|---:|---:|---|
| reference | off | off | off | static |
| bmax_only | on as configured | off | off | static |
| cbusy_only | off | on as configured | off | static |
| combined | on as configured | on as configured | off | static |

Monitor enable remains unchanged. Configured values and seed are preserved.

Cases run sequentially in one background experiment job to avoid host-resource contention changing results.

## Comparison Metrics

Each case reports:

- total throughput and completion ratio;
- maximum P99 latency;
- MC queue peak and time-integrated queue area;
- total MC throttle delay and hard-block events;
- CPU CBusy stall and configured-OSTD stall;
- CBusy transition count.

Per-PARTID comparison reports throughput, P99, queue peak, CBusy stall, throttle, and effective OSTD minimum.

## Causal Timeline

For one selected PARTID and every control interval, the console joins:

- MC achieved bandwidth;
- peak PARTID queue ratio;
- CBusy level and transitions;
- CPU outstanding/effective OSTD;
- cumulative CBusy stall;
- throughput and P99;
- control events delivered at that time.

This is a causal diagnostic view, not proof of physical causality. It exposes temporal ordering and measurable response.

## Diagnostics

The configuration surface reports errors and warnings without changing values:

- BMIN greater than BMAX;
- aggregate enabled BMIN exceeding one MC capacity;
- unordered CBusy thresholds or OSTD caps;
- simultaneous hard BMAX and severe CBusy cap;
- CBusy recovery time longer than the slow control interval;
- no active stimulus or no enabled monitor.
