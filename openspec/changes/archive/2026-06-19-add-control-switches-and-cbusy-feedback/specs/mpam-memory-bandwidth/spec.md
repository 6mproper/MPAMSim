## ADDED Requirements

### Requirement: Independent Memory-Control Enables
The memory-controller MSC SHALL independently enable or disable BMIN, BMAX, priority, and CBusy per PARTID.

#### Scenario: Disable BMAX
- **WHEN** BMAX is disabled for a PARTID
- **THEN** neither hard token blocking nor soft over-limit penalty is applied while BMIN and priority may remain active

#### Scenario: Disable priority
- **WHEN** priority is disabled for a PARTID
- **THEN** its configured priority is retained but the effective scheduling priority contribution is zero

### Requirement: Four-Level PARTID CBusy
Each memory controller SHALL generate a configurable four-level CBusy signal independently for every CBusy-enabled PARTID.

#### Scenario: Assert pressure
- **WHEN** queue pressure, hard-block activity, or contended bandwidth overage crosses an enabled threshold
- **THEN** the MC raises the PARTID to the highest matching CBusy level

#### Scenario: Release pressure
- **WHEN** detector inputs fall below the release condition
- **THEN** CBusy decreases by one level only after the configured release-hold samples

#### Scenario: CBusy disabled
- **WHEN** CBusy is disabled for a PARTID
- **THEN** the MC reports and transmits level zero regardless of detector inputs
