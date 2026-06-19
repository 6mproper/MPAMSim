# Change: Add PARTID Resource Monitor Dashboard

## Why

The current console separates aggregate PARTID, monitor-group, MSC, and control tables, but it does not provide one operational view for following a selected PARTID across the CPU requester, shared L3, and memory controller. CPU outstanding state is also collected only as a requester total and is removed from the interactive API.

## What Changes

- Add interval CPU requester snapshots indexed by PARTID, including current and peak outstanding requests, configured outstanding capacity, issued/completed requests, and requester backpressure.
- Add a resource-oriented monitor dashboard with CPU, L3, and MC views.
- Add 16 independent PARTID visibility controls plus select-all and clear commands.
- Apply the PARTID visibility selection to resource rows and per-PARTID trend charts.
- Show feedback-control state per PARTID using the selected policy, effective resource settings, and latest control update.
- Preserve existing detailed monitor-group, MPAM, MSC, and control-trace views.

## Impact

- Affected specs: interactive-simulation-console, soc-flow-simulation.
- Affected code: requester runtime, metrics collector/export, web job API, interactive HTML/CSS/JavaScript, tests, and monitoring documentation.
- Model boundary: no CPU pipeline, coherency, or architected MPAM register model is introduced.
