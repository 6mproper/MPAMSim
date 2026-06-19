## Context

The core simulator already materializes every CPU hardware thread as an independent requester and can attach one or more workloads to explicit requester IDs. The limitation is in the web configuration builder, which collapses traffic into one `cpu0.t0` latency workload and one multi-core background workload. MPAM controls and monitors are already 16-entry structures, so stimulus should expose equivalent granularity.

## Goals / Non-Goals

**Goals:**

- Provide 16 independently configurable traffic sources corresponding to eight cores and two threads per core.
- Preserve a direct, deterministic mapping between UI row, requester ID, workload, PARTID, and PMG.
- Keep request-count safety checks and common YAML validation.
- Make the default experiment activate all 16 PARTIDs so all monitor rows can be exercised.
- Document the current MPAM model against the broader architectural capability set.

**Non-Goals:**

- Model SMT pipeline contention or cache coherency between sibling threads.
- Implement instruction/data PARTID split, PARTID spaces, RIS, architected feature pages, SMMU/device requesters, PE-side bandwidth shaping, or MPAM domains in this change.
- Replace the general CLI/YAML topology interface with a permanently fixed SoC.

## Decisions

### Fixed interactive reference topology

The web builder will require `active_cores=8` and `threads_per_core=2`. The fields remain visible but read-only so the topology-to-row mapping is unambiguous. The generic schema and CLI remain configurable for other topologies.

### One stimulus row per hardware thread

Rows 0 through 15 map by:

```text
core = floor(row / 2)
thread = row % 2
requester = cpu<core>.t<thread>
```

The requester field is displayed rather than edited. This prevents duplicate or missing thread bindings.

### Independent PARTID and PMG

PARTID and PMG are separately configurable. Defaults map row N to PARTID N and PMG N, but duplicate PARTIDs are allowed because multiple software entities may intentionally share one resource-control partition. PMG remains a monitoring tag rather than a control-table index.

### Unified rate input

Each row selects `MRPS` or `Gbps`; the builder emits exactly one of `injection_rate_mrps` or `injection_rate_gbps`. Since every workload has one requester, rate scope is `per_requester`.

### Policy derivation

Rows with a positive P99 target define protected PARTIDs. Other enabled PARTIDs define the background set. Duplicate IDs are deduplicated, and a protected PARTID is never also classified as background.

### Capability map

The new document will organize capabilities by classification/tagging, transport, MSC controls, monitoring, software discovery/control, and future extensions. Every item will state model status and fidelity so an approximate behavior is not mistaken for architected register implementation.

## Risks / Trade-offs

- [Sixteen active streams can create excessive events] -> Sum estimated requests across all rows and retain the two-million-request web-job guard.
- [A wide 16-row editor can crowd the dashboard] -> Use the existing wide configuration-pane pattern and a horizontally scrollable compact table.
- [Duplicate PARTIDs aggregate result metrics] -> Keep requester identity in timeline data and document that the main KPI table is per PARTID.
- [Fixed web topology may be read as a core-model limitation] -> State explicitly that only the interactive reference scenario is fixed; YAML and Python APIs remain generic.
