# SoC Flow Control / MPAM System Simulation Project

This repository is a Codex-ready project specification and implementation scaffold for building a system-level SoC flow-control simulator focused on MPAM-style partitioning, monitoring, NoC/backpressure behavior, memory-controller bandwidth control, and future closed-loop flow-control policies.

## Project Goal

Build a configurable simulation platform that can answer:

1. Under a given SoC topology, how much interference exists among tenants, VMs, processes, threads, accelerators, and DMA streams?
2. How effective are MPAM-like controls, including PARTID/PMG tagging, cache partitioning, memory-bandwidth allocation, and resource monitoring?
3. Which new system-flow-control policy improves isolation, tail latency, bandwidth fairness, and power-cap compliance beyond static MPAM configuration?
4. What hardware knobs are required in NoC, SLC/L3, DDR/HBM memory controllers, queues, buffers, and rate adapters?

## Repository Layout

```text
docs/
├── PRD.md
├── Architecture.md
├── V1_Scope.md
├── Model_Assumptions.md
├── Evidence_Sources.md
├── User_Interface_and_Visualization.md
├── Stimulus_Model.md
├── Multicore_Model.md
├── MPAM_MSC_Behavior.md
├── MPAM_Model.md
├── FlowControl_Model.md
├── Scenario.md
├── KPI.md
├── API.md
├── Codex_Implementation_Tasks.md
└── Config_Schema.md

src/
├── traffic/
├── noc/
├── cache/
├── ddr/
├── mpam/
├── scheduler/
├── monitor/
├── config/
└── sim/

tests/
├── qos/
├── powercap/
├── noisy_neighbor/
├── llm_inference/
└── llm_training/

examples/
└── baseline_soc.yaml
```

## Recommended First Implementation Path

1. Lock V1 scope and assumptions in `docs/V1_Scope.md` and `docs/Model_Assumptions.md`.
2. Implement the configuration, stimulus, and requester schema in `docs/Config_Schema.md`, `docs/Stimulus_Model.md`, and `docs/Multicore_Model.md`.
3. Implement a deterministic discrete-event simulation kernel.
4. Implement traffic generators and request metadata.
5. Implement MPAM PARTID/PMG tagging, per-MSC settings tables, and monitors using `docs/MPAM_MSC_Behavior.md` as the behavior contract.
6. Implement memory-controller token bucket and priority scheduler.
7. Implement NoC latency, queueing, priority arbitration, and credit/backpressure hooks.
8. Implement cache/SLC capacity approximation; defer exact way-mask replacement.
9. Implement baseline policies: no control, static MPAM, bandwidth cap, priority control, closed-loop QoS.
10. Add CSV/JSON output, report generation, and regression tests for mechanism behavior.

## Non-goals

This simulator is not an RTL model, not a cycle-accurate CPU pipeline model, and not a replacement for silicon validation. It is a system-architecture exploration and control-policy verification platform.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"

python -m src.config.validate --config examples/baseline_soc.yaml
python -m src.sim.run \
  --config examples/baseline_soc.yaml \
  --until-ns 500000 \
  --output outputs/demo

pytest
```

Open `outputs/demo/report.html` to inspect the modeled flow, throughput, tail latency, throttling, and topology.

Run a sweep:

```bash
python -m src.sim.run_sweep \
  --config examples/baseline_soc.yaml \
  --sweep examples/basic_sweep.yaml \
  --until-ns 200000 \
  --output outputs/basic_sweep
```

Run the interactive console:

```bash
python -m src.web.server --host 127.0.0.1 --port 8787
```

Then open `http://127.0.0.1:8787`. The console edits SoC, stimulus, MPAM, and policy parameters, starts simulations as background jobs, and refreshes intermediate control-interval metrics while the run is active.

The interactive reference scenario uses eight cores and two threads per core.
Its stimulus tab exposes 16 independent hardware-thread workloads, matching
the 16 configurable PARTIDs. See `docs/MPAM_Capability_Map.md` for the model's
implemented, approximated, reserved, and out-of-scope MPAM capabilities.

## OpenSpec Workflow

Architecture and behavior changes use OpenSpec:

```bash
openspec list
openspec show <change-name>
openspec validate --all --strict --no-interactive
```

Main capability contracts live under `openspec/specs/`. Completed change
proposals, designs, delta specs, and implementation tasks are retained under
`openspec/changes/archive/`.
