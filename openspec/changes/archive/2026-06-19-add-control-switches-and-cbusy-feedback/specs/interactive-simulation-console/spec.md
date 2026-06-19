## ADDED Requirements

### Requirement: Per-Control Switches
The interactive PARTID editor SHALL expose independent switches for CPBM, CMIN, CMAX, BMIN, BMAX, priority, and CBusy.

#### Scenario: Disable one mechanism
- **WHEN** the operator disables one control switch
- **THEN** its configured value remains visible but the result monitor reports that mechanism as disabled and shows its neutral effective value

### Requirement: CBusy Configuration And Evidence
The console SHALL configure CBusy timing/threshold parameters and per-level OSTD caps and SHALL display the resulting feedback evidence.

#### Scenario: Observe CBusy feedback
- **WHEN** an MC raises CBusy for a selected PARTID
- **THEN** the MC view shows detector level/inputs and the CPU view shows the matching effective OSTD and CBusy stall

#### Scenario: Compare mechanisms
- **WHEN** runs differ only in BMAX and CBusy enable switches
- **THEN** exported and live metrics are sufficient to compare queueing, latency, throughput, source stall, and control transitions
