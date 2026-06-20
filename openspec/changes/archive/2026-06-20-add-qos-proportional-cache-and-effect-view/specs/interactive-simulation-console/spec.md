## MODIFIED Requirements

### Requirement: Per-Control Switches
The PARTID editor SHALL expose independent switches for CPBM, proportional
CMIN, proportional CMAX, BMIN, BMAX, 3-bit MC QoS, and CBusy.

#### Scenario: Configure proportional cache and MC QoS
- **WHEN** the operator edits a PARTID row
- **THEN** CMIN/CMAX use percentage units and MC QoS accepts zero through seven

## ADDED Requirements

### Requirement: Structured Algorithm Explanations
The console SHALL show an anchored algorithm explanation when the pointer
hovers over a tagged control, flow stage, or result metric.

#### Scenario: Inspect an algorithm
- **WHEN** the pointer rests on CMIN, CMAX, BMIN, BMAX, MC QoS, CBusy, or OSTD
- **THEN** the window shows formula, activation rules, monitor evidence, model version, and boundary without overlapping the target

### Requirement: PARTID Control-Effect Overview
The console SHALL summarize all 16 PARTIDs by configured targets, latest
actual resource shares, full-run adherence, effective QoS, P99 target/result,
and state.

#### Scenario: Scan control health
- **WHEN** a simulation has interval data
- **THEN** each PARTID row distinguishes satisfied, borrowing, inactive, limited, and violation states

### Requirement: Selected-PARTID Full-Run Effect
The console SHALL show synchronized full-run target and actual trends for one
selected PARTID.

#### Scenario: Inspect one PARTID
- **WHEN** the operator selects a PARTID
- **THEN** L3 share, MC bandwidth, base/effective QoS, P99, throughput, flow-control evidence, and control events are aligned by time
