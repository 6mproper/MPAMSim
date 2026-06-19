## Context

The repository starts with no implementation. The target is an architecture-exploration simulator that exposes causal flow-control effects without the cost or false precision of RTL, cache coherency, CPU pipeline, or detailed DRAM timing models. The primary users are SoC architects evaluating contention, MPAM-style resource controls, multicore stimulus, and closed-loop QoS policies.

## Goals / Non-Goals

**Goals:**

- Model the request path from multicore workload generation through NoC, shared L3/SLC, and memory controllers.
- Keep the model deterministic under a fixed seed and configurable without source edits.
- Represent MPAM settings independently at each MSC and expose enough monitor state to explain latency, bandwidth, queueing, and throttling.
- Provide both automation-oriented outputs and an interactive local console.
- Preserve modular interfaces for future NoC, cache, memory, requester-shaping, and policy refinements.

**Non-Goals:**

- Cache coherency, snoop traffic, invalidation, and dirty sharing.
- Cycle-accurate CPU pipelines, instruction execution, and detailed cache replacement across all sets.
- Full Arm MPAM register, exception, security-state, ACPI, or Linux resctrl behavior.
- Detailed DRAM banks, rows, timing constraints, refresh, and power modeling.

## Decisions

### Deterministic discrete-event kernel

Use a Python `heapq` event kernel with explicit timestamps and stable sequencing. This is lightweight, reproducible, and adequate for system-level queueing and control-policy experiments. A cycle-accurate framework was rejected for V1 because its calibration burden would exceed the fidelity of the other abstract components.

### Typed configuration with one schema path

Load YAML into dataclasses and validate topology, workloads, MPAM controls, and outputs before simulation. The web console converts form state into the same schema, avoiding a second internal model.

### Modular request pipeline

Represent requests with requester, PARTID, PMG, address, size, operation, priority, and latency-attribution fields. Components add queue, service, cache, NoC, and throttle delays without depending on workload implementation details.

### Per-MSC MPAM settings

Instantiate a 16-entry settings table at every L3 and memory controller. Controls are local to an MSC; UI values shown across multiple instances are explicitly summed. The `no_control` policy preserves settings and monitors while disabling NoC priority mapping and L3/MC enforcement.

### Approximate L3 set/way monitor

Configure explicit set count, ways per set, and line size. Enforce CPBM and CMAX in sampled sets, and protect CMIN ownership during sampled replacement. Store tags and PARTID ownership only for the first set in every eight-set group, then scale access and occupancy observations by eight. This preserves set/way control directionality at bounded cost while clearly labeling results as estimates.

### Memory bandwidth semantics

Use independent per-PARTID token state at each memory controller. Hard limit requests wait for BMAX tokens. Soft limit requests remain eligible but receive an over-limit scheduling penalty only during contention. BMIN provides a reservation-oriented priority bonus when credit is available. Aging prevents permanent starvation.

### Local operational UI

Serve static HTML, CSS, and JavaScript plus JSON job endpoints using Python's standard `ThreadingHTTPServer`. Simulations execute as background jobs and publish interval snapshots for polling. This avoids a frontend build dependency while retaining direct parameter entry, dynamic charts, tables, and report links.

### Evidence and outputs

Export resolved configuration, topology, run summary, per-PARTID metrics, per-MSC utilization, control trace, and timeline trace. Keep architecture assumptions and external evidence boundaries documented separately.

## Risks / Trade-offs

- [Approximate L3 occupancy can diverge from a full tag array] -> Label sampled and estimated values, keep the eight-set factor explicit, and validate directional behavior rather than claiming cycle accuracy.
- [BMIN is not a strict real-time guarantee] -> Define it as a scheduler reservation approximation and expose achieved bandwidth and queue delays.
- [Per-MC controls can be misread as system totals] -> Mark aggregated UI columns with `Σ` and document that token state is independent per controller.
- [High-rate workloads can create excessive events] -> Validate duration, intervals, queue sizes, and estimated request count before starting a web job.
- [Simple polling limits visualization update rate] -> Keep the API schema stable so WebSocket or streaming transport can replace polling later.

## Migration Plan

1. Add OpenSpec artifacts and capability contracts.
2. Add implementation, examples, tests, and documentation at repository root.
3. Run configuration validation, Python compilation, JavaScript syntax checks, and pytest.
4. Archive the completed OpenSpec change so its delta specs become the repository's main specifications.
5. Push a normal fast-forward commit to `main`.

Rollback is a standard Git revert of the implementation commit.

## Open Questions

- What traffic traces or silicon counters will calibrate cache hit probability, BMIN behavior, and memory service latency?
- Should future releases model PMG independently from PARTID in every monitor?
- Which downstream congestion signal should drive requester-side MPAM soft bandwidth control?
