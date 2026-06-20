# Change: Add L3 Queue And Control Verification

## Why

The cache model currently accepts unlimited concurrent lookups and reports zero
queue occupancy, so requester OSTD cannot create observable L3 admission
pressure. The control algorithms are implemented but their hard-coded
scheduler constants and mechanism-specific evidence are difficult to inspect
or validate from the console.

## What Changes

- Add a bounded FIFO request queue and configurable lookup parallelism to every
  L3/SLC instance.
- Attribute L3 queue delay, admission backpressure, full events, average/peak
  queue occupancy, and active lookup slots.
- Correct sampled replacement so a PARTID below CMAX can grow by evicting an
  owner above its effective CMIN.
- Expose memory-controller token window, aging quantum, aging cap, BMIN
  priority boost, and soft-limit priority penalty through YAML and the web
  console.
- Add a deterministic control-verification suite for CMIN, CMAX, BMIN, BMAX
  soft limit, and BMAX hard limit, with explicit pass criteria and evidence.
- Document the current model algorithms and distinguish them from
  implementation-defined Arm MPAM microarchitecture.

## Impact

- Affected specs: `mpam-l3-control`, `mpam-memory-bandwidth`,
  `interactive-simulation-console`, and `soc-flow-simulation`.
- Affected code: configuration schema/loader/validator, L3 and MC models,
  web configuration/job APIs, monitoring UI, tests, and model documentation.
