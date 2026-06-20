## ADDED Requirements

### Requirement: Deterministic Mechanism Experiment
The console SHALL run reference, BMAX-only, CBusy-only, and combined cases from one submitted configuration using identical topology, stimulus, duration, and seed.

#### Scenario: Run comparison
- **WHEN** the operator starts a mechanism experiment
- **THEN** all four cases run sequentially with static policy and differ only in BMAX and CBusy enable state

### Requirement: Experiment Effect Comparison
The console SHALL compare control benefit and cost overall and for a selected PARTID.

#### Scenario: Inspect overall effect
- **WHEN** the experiment completes
- **THEN** the console reports throughput, P99, completion, queue peak/area, throttle, source stall, hard blocks, and CBusy transitions for every case

#### Scenario: Inspect one PARTID
- **WHEN** the operator selects a PARTID
- **THEN** the console reports that PARTID's throughput, P99, queue pressure, effective OSTD, CBusy stall, and throttle across all four cases

### Requirement: Causal Timeline
The console SHALL join pressure, feedback, source enforcement, and workload response by PARTID and control interval.

#### Scenario: Follow a feedback event
- **WHEN** CBusy changes for the selected PARTID
- **THEN** the same timeline shows MC pressure, CBusy level, effective OSTD, source stall, throughput, P99, and associated control events

### Requirement: Configuration Diagnostics
The console SHALL identify invalid and risky control combinations before a run.

#### Scenario: Overcommitted reservation
- **WHEN** aggregate enabled BMIN exceeds one MC capacity
- **THEN** the console shows an explicit warning with the configured sum and capacity

#### Scenario: Aggressive double throttle
- **WHEN** hard BMAX and a severe CBusy OSTD cap are enabled together
- **THEN** the console warns that queue reduction may incur excess throughput loss
