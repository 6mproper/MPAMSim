## Why

The simulator exposes 16 MPAM partitions but its interactive stimulus is still reduced to one protected workload and one background workload. That prevents thread-level validation of PARTID/PMG assignment and cannot represent the requested eight-core, sixteen-thread traffic matrix.

## What Changes

- Fix the interactive reference topology to eight cores with two hardware threads per core.
- Replace the two-workload form with a 16-row stimulus editor mapped one-to-one to `cpu0.t0` through `cpu7.t1`.
- Allow each thread stimulus to configure enable state, PARTID, PMG, workload type, rate and unit, request size, read ratio, working set, and optional P99 target.
- Generate one validated workload per enabled hardware-thread stimulus.
- Derive closed-loop protected and background PARTID sets from the configured thread targets.
- Add an MPAM capability map that distinguishes implemented, approximated, interface-reserved, and out-of-scope architectural features using the supplied Arm analysis documents and their official references.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `interactive-simulation-console`: Replace the two-class traffic form with a configurable 16-thread stimulus matrix.
- `soc-flow-simulation`: Materialize 16 independent workloads for the eight-core, two-thread interactive reference topology.

## Impact

- Changes web configuration payloads from legacy protected/background fields to `stimulus_configs`.
- Updates the web configuration builder, static UI, tests, stimulus documentation, and MPAM capability documentation.
- Does not change the generic YAML loader or prevent non-8-core topologies from being modeled through the CLI/Python API.
