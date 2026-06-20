## ADDED Requirements

### Requirement: Reproducible Control-Mechanism Comparison
The simulator SHALL derive mechanism-isolation cases without modifying workload, topology, duration, or seed.

#### Scenario: Derive experiment cases
- **WHEN** a valid configuration is submitted for comparison
- **THEN** the four derived configurations preserve all non-control inputs and use static policy

#### Scenario: Summarize queue effect
- **WHEN** a comparison case completes
- **THEN** the result includes MC queue peak and time-integrated queue area in addition to latency, throughput, and control counters
