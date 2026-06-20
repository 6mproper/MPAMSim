# Change: Add Experiment Comparison And Causal Timeline

## Why

The console can configure and monitor individual control mechanisms, but an operator must still run cases manually and correlate multiple tables to decide whether control improved the system. This makes mechanism validation slow and error-prone.

## What Changes

- Add one-command deterministic four-case experiments using identical topology, stimulus, duration, and seed:
  - reference with BMAX and CBusy disabled;
  - BMAX only;
  - CBusy only;
  - BMAX plus CBusy.
- Force static policy during the mechanism experiment so the slow software loop cannot confound the comparison.
- Summarize throughput, tail latency, MC queue peak/area, throttle, source stall, hard blocks, CBusy transitions, and completion ratio.
- Add per-PARTID experiment comparison.
- Add a per-PARTID causal timeline joining MC pressure, CBusy, effective OSTD, source stall, P99, throughput, and control events.
- Add live configuration diagnostics for invalid or risky combinations such as aggregate BMIN overcommit and aggressive double throttling.

## Impact

- Affected specs: interactive-simulation-console and soc-flow-simulation.
- Affected code: web job server, experiment summaries, UI actions/result views, diagnostics, tests, and documentation.
