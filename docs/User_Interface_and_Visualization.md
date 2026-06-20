# User Interface and Visualization

## 1. Interface Goal

V1 does not require a full GUI, but it must provide a user-facing control surface and visualization-ready outputs. Users must be able to configure topology, stimulus, MPAM controls, flow-control policies, and output reports without editing simulator code.

The interface stack is:

```text
YAML/JSON config -> CLI/Python API -> simulation outputs -> generated plots or HTML report
```

## 2. Required V1 User Interfaces

### 2.1 Configuration Files

Configuration files are the primary user interface for V1.

They must cover:

- SoC topology.
- Requesters and multicore mapping.
- Workload stimulus.
- MPAM PARTID/PMG mapping.
- MSC capabilities and control settings.
- Flow-control policy parameters.
- Sweep parameters.
- Output and visualization settings.

### 2.2 CLI

The CLI must support:

```bash
python -m src.config.validate --config examples/baseline_soc.yaml
python -m src.sim.run --config examples/baseline_soc.yaml
python -m src.sim.run --config examples/baseline_soc.yaml --scenario tests/noisy_neighbor/basic.yaml
python -m src.sim.run_sweep --config examples/baseline_soc.yaml --sweep tests/qos/core_l3_sweep.yaml
python -m src.monitor.report --run outputs/noisy_neighbor --format html
```

### 2.3 Python API

The Python API is required for architecture experiments, notebooks, and regression tests.

```python
cfg = load_config("examples/baseline_soc.yaml")
sim = Simulation.from_config(cfg)
result = sim.run()
result.export("outputs/run_001")
result.render_report("outputs/run_001/report.html")
```

### 2.4 Interactive Local Console

The implemented local console is started with:

```bash
python -m src.web.server --host 127.0.0.1 --port 8787
```

It provides:

- Direct numeric configuration for multicore topology, L3/SLC, NoC, and memory controllers.
- A 16-row stimulus editor mapped to `cpu0.t0` through `cpu7.t1`, with
  independent PARTID, PMG, workload type, rate, request size, read ratio,
  working set, and P99 target.
- A 16-row PARTID editor for monitor enable, CMIN, CMAX, CPBM, BMIN, BMAX,
  softlimit/hardlimit, and priority.
- Explicit L3 set count, ways per set, line size, bounded request queue,
  lookup parallelism, and fixed eight-set approximate-monitor grouping.
- Policy selection and closed-loop stability parameters.
- Configurable MC token-bucket window, aging quantum/cap, BMIN priority boost,
  and soft-limit priority penalty.
- Background simulation jobs with control-interval progress updates.
- Dynamic charts, time-slider playback, MSC tables, control traces, and links to static reports.
- A 16-row MPAM monitor table with sampled L3 bandwidth/occupancy and
  memory-controller bandwidth/limit events. Columns marked `Σ` are sums
  across all configured L3 or memory-controller instances.
- Contextual help on configuration categories, fields, abbreviated table
  columns, policies, and result views. Hover and keyboard focus use the same
  tooltip content.
- A live `PARTID+PMG` monitor-group table updated at control intervals. It
  shows requester membership, estimated L3 occupancy/utilization, L3 sampled
  bandwidth, MC achieved bandwidth/utilization, requests, and throttle delay.
- A resource-oriented PARTID dashboard with CPU, L3, and MC modes. CPU shows
  current/interval-peak outstanding requests and source backpressure; L3 shows
  sampled occupancy/bandwidth and effective cache controls; MC shows
  bandwidth, queueing, throttling, and effective bandwidth controls.
- Independent visibility toggles for PARTID 0 through 15. The selection
  filters the resource table, per-PARTID trend charts, PARTID details, MPAM
  aggregate monitor, monitor groups, and control trace without changing the
  simulation configuration.
- Per-PARTID feedback state that distinguishes no control, static control,
  closed-loop monitoring, and runtime-adjusted control, with the latest update
  target, field, time, and reason.
- Independent per-PARTID switches for CPBM, CMIN, CMAX, BMIN, BMAX,
  priority, and CBusy. A disabled control keeps its configured value visible
  while the resource monitor shows the neutral effective value.
- CBusy fast-loop configuration for detector period, feedback latency,
  release hold, bandwidth/queue thresholds, and per-PARTID level-1/2/3 OSTD
  caps.
- CPU and MC resource views expose the causal chain: MC CBusy inputs/level,
  requester effective OSTD, CBusy source stall, queueing, latency, and
  throughput cost.
- A one-command four-case experiment holds topology, stimulus, duration, and
  seed constant while comparing reference, BMAX-only, CBusy-only, and
  combined control. It reports overall and selected-PARTID deltas and links
  each case to its static report.
- A selected-PARTID causal timeline aligns MC bandwidth/queue pressure, CBusy
  level, CPU outstanding/effective OSTD, source stall, P99, throughput, and
  delivered control events at each control interval.
- Live configuration diagnostics identify invalid or risky combinations such
  as BMIN/BMAX inversion, aggregate BMIN overcommit, unordered CBusy
  thresholds/caps, disabled monitoring on active PARTIDs, and stacked hard
  BMAX plus CBusy throttling. Diagnostics never rewrite the user's values.
- A built-in algorithm-verification view runs deterministic CMIN, CMAX, BMIN,
  BMAX soft-limit, and BMAX hard-limit microbenchmarks and reports explicit
  pass criteria, evidence, case counters, and report links.

## 3. Visualization Requirements

V1 visualization may be static HTML/PNG/CSV. It does not need a live web GUI.

Required report views:

- Run summary: topology, policies, workloads, key KPIs.
- Per-PARTID latency: average, p95, p99, p999 over time.
- Per-PARTID bandwidth over time.
- Per-MSC queue occupancy over time.
- L3/SLC occupancy and hit/miss rate per PARTID.
- Memory-controller utilization and throttle delay.
- Control timeline: every policy update with old value, new value, target MSC, PARTID, and reason.
- Bottleneck attribution: NoC delay, cache delay, memory queue delay, service delay, throttle delay.

Recommended views:

- Topology graph with requesters, NoC nodes, L3/SLC, and memory controllers.
- Heatmap for per-MSC utilization.
- Baseline-vs-controlled comparison.
- Policy stability plot showing cap and priority changes.

## 4. Visualization Output Files

The simulator should emit visualization-ready data:

```text
run_summary.json
metrics.csv
per_cpu_partid.csv
per_partid_latency.csv
per_msc_utilization.csv
control_trace.csv
timeline_trace.csv
topology.json
report.html
```

`report.html` may be generated after the simulation from the CSV/JSON files. Keeping report generation separate prevents visualization from polluting simulation semantics.

## 5. Live UI Boundary

The implemented live GUI consumes the same validated configuration and output
schemas as CLI/Python runs. It does not introduce an independent simulation
or control path.

Additional GUI panels should continue to map to existing concepts:

- Topology editor.
- Workload/stimulus editor.
- MPAM MSC control table editor.
- Policy parameter editor.
- Timeline viewer.
- Result comparison dashboard.
