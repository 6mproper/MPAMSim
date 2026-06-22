## MODIFIED Requirements

### Requirement: L3 allocation controls
The L3 model SHALL apply CPBM as the eligible-way mask, CMAX as the maximum
percentage of physical L3 capacity owned by a PARTID, and CMIN as the minimum
percentage protected from replacement after demand has populated lines.

#### Scenario: Restrict proportional allocation
- **WHEN** a PARTID reaches its effective CMAX percentage
- **THEN** its aggregate ownership across sampled sets cannot grow further

#### Scenario: Protect proportional minimum
- **WHEN** a victim PARTID is at or below its effective CMIN sampled-line target
- **THEN** another PARTID cannot evict that victim

## ADDED Requirements

### Requirement: Proportional Control Validation
The configuration SHALL require each enabled CMIN/CMAX pair to satisfy
`0 <= CMIN <= CMAX <= 100`, SHALL reject enabled CMIN totals above 100%, and
SHALL reject CMIN above the effective CPBM reachable percentage.

#### Scenario: Overcommit CMIN
- **WHEN** enabled CMIN percentages on one L3 sum above 100%
- **THEN** configuration validation fails with the configured sum

#### Scenario: CMAX totals exceed 100%
- **WHEN** multiple CMAX percentages sum above 100%
- **THEN** configuration remains valid because CMAX is a per-PARTID ceiling
