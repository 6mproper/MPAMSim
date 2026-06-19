## ADDED Requirements

### Requirement: Independent L3 Control Enables
The L3 MSC SHALL independently enable or disable CPBM, CMIN, and CMAX per PARTID while retaining configured values for monitoring and later re-enable.

#### Scenario: Disable CPBM only
- **WHEN** CPBM is disabled and CMAX remains enabled for a PARTID
- **THEN** every physical way is eligible while the configured CMAX still limits allocation

#### Scenario: Disable CMIN only
- **WHEN** CMIN is disabled for a PARTID
- **THEN** replacement applies no minimum-way protection for that PARTID while CPBM and CMAX retain their enabled behavior

#### Scenario: Disable CMAX only
- **WHEN** CMAX is disabled for a PARTID
- **THEN** the effective maximum equals the number of ways allowed by the effective CPBM
