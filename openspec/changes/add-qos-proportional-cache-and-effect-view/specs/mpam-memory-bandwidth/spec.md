## MODIFIED Requirements

### Requirement: Sixteen PARTID memory settings
Each memory-controller MSC SHALL expose independent bandwidth settings, token
state, 3-bit MC QoS, and monitoring entries for exactly 16 PARTIDs numbered
zero through 15.

#### Scenario: Configure MC QoS
- **WHEN** software configures a PARTID MC QoS value
- **THEN** the accepted value is in `[0, 7]` and is local to MC arbitration

### Requirement: BMAX soft limit
The memory-controller model SHALL keep soft-limit traffic eligible and SHALL
demote its effective MC QoS only while it is over BMAX and contending.

#### Scenario: Uncontended soft-limit traffic
- **WHEN** a PARTID exceeds BMAX without another eligible contender
- **THEN** its effective MC QoS is not demoted and service remains work-conserving

#### Scenario: Contended soft-limit traffic
- **WHEN** a PARTID exceeds BMAX while another request is eligible
- **THEN** its effective MC QoS is reduced by the configured bounded demotion

### Requirement: BMIN reservation approximation
The memory-controller scheduler SHALL promote effective MC QoS for a candidate
whose request is covered by BMIN credit.

#### Scenario: Compete below BMIN
- **WHEN** a request is covered by BMIN credit
- **THEN** its effective QoS is promoted by the configured bounded number of levels

## ADDED Requirements

### Requirement: 3-bit QoS Arbitration
The MC scheduler SHALL choose the highest effective QoS candidate and SHALL
choose the oldest request when effective QoS values are equal.

#### Scenario: Clamp QoS adjustments
- **WHEN** aging, BMIN promotion, or soft demotion changes QoS
- **THEN** effective QoS remains within zero through seven

#### Scenario: Hard limit blocks a high-QoS request
- **WHEN** a QoS-seven hard-limited request lacks tokens
- **THEN** it is excluded from arbitration until tokens are available
