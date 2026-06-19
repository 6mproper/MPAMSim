## Why

SoC architecture exploration needs a reproducible model that connects multicore traffic, shared-resource contention, MPAM controls, and user-visible measurements. The repository currently contains no simulator, so this change establishes a complete V1 baseline while deliberately excluding cache coherency and cycle-accurate CPU behavior.

## What Changes

- Add a deterministic Python discrete-event simulator for requester, NoC, L3/SLC, and memory-controller flow.
- Add configurable multicore topology and workload stimulus through YAML, CLI, Python APIs, and a local web console.
- Add exactly 16 configurable PARTIDs at every L3 and memory-controller MSC.
- Add L3 CMIN, CMAX, and CPBM enforcement with an approximate one-in-eight-set monitor.
- Add per-memory-controller BMIN and BMAX behavior with work-conserving soft limits and token-bucket hard limits.
- Add dynamic charts, MPAM monitor tables, CSV/JSON traces, topology export, and static HTML reports.
- Add regression tests for configuration, determinism, cache partitioning, bandwidth limiting, priority, multicore scaling, reports, and the 16-PARTID model.
- Keep coherency, detailed DRAM timing, CPU pipelines, full MPAM registers, ACPI, and Linux resctrl outside V1.

## Capabilities

### New Capabilities

- `soc-flow-simulation`: Deterministic system-level modeling of multicore request injection and NoC/cache/memory contention.
- `mpam-l3-control`: Sixteen-PARTID L3 allocation control and approximate set/way monitoring.
- `mpam-memory-bandwidth`: Sixteen-PARTID memory-controller bandwidth monitoring and BMIN/BMAX control.
- `interactive-simulation-console`: Direct configuration, execution, dynamic visualization, and report access through a local web interface.

### Modified Capabilities

None.

## Impact

- Adds the Python package under `src/`, configuration examples, architecture documents, tests, and web assets.
- Runtime dependency: PyYAML. Test dependency: pytest.
- Adds OpenSpec project metadata, capability specifications, and an archived implementation change.
- Introduces no external service dependency; the web console is served locally with Python's standard HTTP server.
