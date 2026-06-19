# Change: Add Independent Control Switches And CBusy Feedback

## Why

The simulator currently couples configured values to enforcement and cannot isolate the effect of each mechanism. It also limits traffic mainly at the memory controller, so queue growth cannot be reduced through a fast per-PARTID source-feedback loop.

## What Changes

- Add independent per-PARTID enable switches for CPBM, CMIN, CMAX, BMIN, BMAX, priority, and CBusy feedback.
- Preserve configured values while a mechanism is disabled and report both configured and effective values.
- Add configurable four-level per-PARTID CBusy generation at each memory controller.
- Aggregate CBusy from multiple memory controllers with the maximum level and apply a per-PARTID effective OSTD cap at CPU requesters.
- Separate ordinary maximum-OSTD stall from CBusy-induced source stall.
- Add CBusy thresholds, feedback latency, release hysteresis/hold time, and per-level OSTD caps.
- Extend live monitoring and exports with CBusy level, effective OSTD, transitions, duty, and source-stall evidence.
- Add deterministic mechanism-isolation tests for no control, BMAX only, CBusy only, and combined control.

## Impact

- Affected specs: mpam-l3-control, mpam-memory-bandwidth, soc-flow-simulation, interactive-simulation-console.
- Affected code: configuration schema/validation, MPAM settings, cache/MC enforcement, requester runtime, simulation feedback wiring, monitors, web configuration and resource dashboard, tests, and documentation.
- The four levels and thresholds are simulator-configurable behavior, not claimed architected encodings.
