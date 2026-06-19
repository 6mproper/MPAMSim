## ADDED Requirements

### Requirement: CBusy-Controlled Effective OSTD
The requester SHALL apply delayed per-PARTID CBusy feedback as an effective outstanding-request cap without replacing the configured requester maximum.

#### Scenario: Multiple MC feedback
- **WHEN** multiple memory controllers report CBusy for the same PARTID
- **THEN** the requester uses the maximum reported level and the corresponding configured OSTD cap

#### Scenario: CBusy source stall
- **WHEN** PARTID outstanding reaches the CBusy-derived cap before the requester-wide maximum
- **THEN** new requests retry and the delay is recorded as CBusy stall rather than configured-OSTD stall

#### Scenario: Preserve forward progress
- **WHEN** level 3 CBusy is active
- **THEN** the effective OSTD remains at least one and already-issued requests can complete
