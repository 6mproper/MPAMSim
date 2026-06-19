# Codex Implementation Tasks

## Global Instruction to Codex

Implement a clean, testable Python simulation framework. Keep modules small. Use dataclasses and type hints. Prefer deterministic behavior under fixed seed. Do not hard-code topology. All hardware parameters must be loaded from YAML.

V1 is focused on SoC-level flow control and MPAM-style partitioning/monitoring. Cache coherency, full MPAM register behavior, full ACPI/Linux resctrl integration, detailed DRAM timing, exact cache replacement, and full power-cap modeling are out of scope until the baseline QoS mechanisms are proven.

## Phase 0: Project Setup

Tasks:

1. Create Python package structure under `src/`.
2. Add `pyproject.toml` or `requirements.txt`.
3. Add dependency: `pyyaml`, `numpy`, `pandas`, `pytest`.
4. Add `README.md` run instructions.
5. Add `examples/baseline_soc.yaml` as first working example.

Acceptance:

```bash
python -m src.config.validate --config examples/baseline_soc.yaml
pytest
```

## Phase 1: Configuration Loader

Implement:

```text
src/config/schema.py
src/config/loader.py
src/config/validator.py
```

Requirements:

- Load YAML into typed dataclasses.
- Validate unique IDs.
- Validate each core maps to exactly one L3/SLC.
- Validate each PARTID referenced by workloads exists in MPAM partitions.
- Validate each MSC control targets an existing MSC.
- Validate bandwidth and cache masks are valid.
- Validate requesters, requester-to-NoC attachment, and max outstanding settings.
- Validate visualization/report output settings.

## Phase 2: Discrete-Event Kernel

Implement:

```text
src/sim/event.py
src/sim/kernel.py
src/sim/component.py
```

Requirements:

- Priority queue of events.
- `schedule(time_ns, callback)`.
- `run(until_ns)`.
- Deterministic ordering for same timestamp.

## Phase 3: Traffic Generator

Implement:

```text
src/traffic/request.py
src/traffic/requester.py
src/traffic/generator.py
src/traffic/workload.py
```

Requirements:

- Materialize multicore CPU threads, DMA, accelerator, PCIe, and synthetic tenant requesters.
- Generate requests with ID, requester ID, PARTID, PMG, address, size, op, issue timestamp.
- Support stream and random patterns.
- Support fixed and Poisson inter-arrival time.
- Support burst mode.
- Support phase-based stimulus.

## Phase 4: MPAM Settings and Monitors

Implement:

```text
src/mpam/partid.py
src/mpam/settings.py
src/mpam/control.py
src/mpam/monitor.py
```

Requirements:

- Settings table per MSC.
- Lookup by PARTID.
- Apply update at runtime.
- Monitor counters per PARTID and optionally per PMG.
- Implement the common MSC behavior contract in `docs/MPAM_MSC_Behavior.md`.

## Phase 5: Memory Controller MSC

Implement:

```text
src/ddr/memctrl.py
src/ddr/channel.py
src/ddr/scheduler.py
```

Requirements:

- Token-bucket bandwidth cap per PARTID.
- Priority-aware request scheduler.
- Track queue occupancy and service latency.
- Track per-controller/channel utilization.
- Attribute delay into throttle delay, queue delay, and service delay.

## Phase 6: NoC MSC

Implement:

```text
src/noc/router.py
src/noc/link.py
src/noc/queue.py
src/noc/topology.py
src/noc/flow_control.py
```

Requirements:

- Model fixed per-hop latency.
- Model queueing delay based on queue occupancy.
- Support priority scheduling.
- Support credit/backpressure hooks.
- Attribute NoC delay separately from memory-controller delay.

## Phase 7: Cache MSC

Implement:

```text
src/cache/cache_msc.py
src/cache/replacement.py
src/cache/partition.py
```

Requirements:

- Start with capacity approximation.
- Defer exact way-mask model until V1 bandwidth and priority behavior is proven.
- Enforce cache portion bitmap.
- Track hit/miss/occupancy per PARTID.

## Phase 8: Policies

Implement:

```text
src/scheduler/policy_base.py
src/scheduler/no_control.py
src/scheduler/static_mpam.py
src/scheduler/priority_policy.py
src/scheduler/closed_loop.py
```

Requirements:

- Policy plug-in interface.
- Periodic monitor snapshot.
- Generate control updates.
- Log all control updates.
- Include hysteresis, minimum hold intervals, step limits, and configured floors/ceilings for closed-loop control.

## Phase 9: Metrics and Export

Implement:

```text
src/monitor/metrics.py
src/monitor/collector.py
src/monitor/exporter.py
src/monitor/report.py
src/monitor/plots.py
```

Requirements:

- Calculate average, p95, p99, p999 latency.
- Export CSV and JSON.
- Export control trace.
- Export timeline trace and topology JSON for visualization.
- Generate a static HTML report from output files.

## Phase 10: Tests

Add tests:

```text
tests/qos/test_bandwidth_cap.py
tests/qos/test_priority_latency.py
tests/noisy_neighbor/test_no_control_vs_mpam.py
tests/test_config_validation.py
```

Minimum test expectations:

- Bandwidth cap limits achieved bandwidth.
- Higher priority improves latency under contention.
- Cache mask changes occupancy.
- Invalid config fails validation.
- Fixed seed gives deterministic output.
- Credit/backpressure reduces sustained queue buildup.
- Report generation consumes exported output without rerunning simulation.

## Phase 11: Deferred Extensions

Add after V1 is validated:

```text
src/scheduler/powercap_policy.py
tests/powercap/test_powercap_policy.py
tests/llm_inference/
tests/llm_training/
exact cache way model
detailed DRAM timing
software/firmware discovery models
```

## First Codex Prompt

Use this prompt to start implementation:

```text
Implement the V1 SoC Flow Control / MPAM system simulator based on this repository. Start with Python and follow docs/V1_Scope.md, docs/Model_Assumptions.md, docs/Stimulus_Model.md, docs/Multicore_Model.md, docs/MPAM_MSC_Behavior.md, and docs/User_Interface_and_Visualization.md. Build the configuration loader, deterministic discrete-event kernel, requester/stimulus generator, MPAM settings table, monitors, memory-controller token-bucket bandwidth model, NoC latency/queue/priority model, simplified cache capacity-approximation MSC, CSV/JSON exporter, topology/timeline trace export, and static HTML report generator. Use examples/baseline_soc.yaml as the first runnable scenario. Add pytest tests for config validation, bandwidth cap, priority latency, cache partition directionality, credit/backpressure queue reduction, deterministic seed behavior, and report generation. Keep topology fully configurable; do not hard-code core count, thread count, L3/SLC sharing, requester attachment, or memory-controller count. Do not implement cache coherency, exact cache way replacement, full MPAM register behavior, full Linux resctrl/ACPI integration, detailed DRAM timing, live GUI, or powercap until V1 QoS mechanisms are validated.
```
