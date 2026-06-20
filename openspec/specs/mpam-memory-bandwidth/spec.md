# mpam-memory-bandwidth Specification

## Purpose
Define per-memory-controller, per-PARTID bandwidth reservation, limiting,
scheduling, and monitoring behavior.
## Requirements
### Requirement: Sixteen PARTID memory settings
Each memory-controller MSC SHALL expose independent bandwidth settings, token
state, 3-bit MC QoS, and monitoring entries for exactly 16 PARTIDs numbered
zero through 15.

#### Scenario: Configure MC QoS
- **WHEN** software configures a PARTID MC QoS value
- **THEN** the accepted value is in `[0, 7]` and is local to MC arbitration

### Requirement: BMAX hard limit
The memory-controller model SHALL implement hard BMAX as a per-PARTID token bucket that blocks dispatch until sufficient tokens exist.

#### Scenario: Exceed a hard limit
- **WHEN** a queued request lacks BMAX tokens in `hardlimit` mode
- **THEN** dispatch waits, throttle delay increases, and a hard-limit block event is monitored

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

### Requirement: Bandwidth monitoring
The memory-controller monitor SHALL report achieved bandwidth, configured
BMIN and BMAX, limit mode, base/effective MC QoS, queue delay, service delay,
throttle delay, soft-limit requests, and hard-limit block events per PARTID.

#### Scenario: Display aggregate results
- **WHEN** the interactive console combines multiple memory-controller snapshots
- **THEN** aggregate bandwidth and configured limits are labeled as sums across controller instances

### Requirement: PMG-scoped memory bandwidth monitoring
The memory-controller monitor SHALL attribute serviced requests and bytes to `(PARTID, PMG)` monitor groups while retaining PARTID-only bandwidth enforcement.

#### Scenario: Service a monitor-group request
- **WHEN** the memory controller dispatches a request with PARTID P and PMG G
- **THEN** the corresponding group counters record requests, bytes, queue delay, service delay, and applicable limit events

#### Scenario: Report group bandwidth utilization
- **WHEN** a memory-controller interval snapshot is captured
- **THEN** each active monitor group reports achieved bandwidth and utilization relative to that controller's total modeled bandwidth

### Requirement: Independent Memory-Control Enables
The memory-controller MSC SHALL independently enable or disable BMIN, BMAX,
MC QoS, and CBusy per PARTID.

#### Scenario: Disable BMAX
- **WHEN** BMAX is disabled for a PARTID
- **THEN** neither hard token blocking nor soft over-limit demotion is applied while BMIN and MC QoS may remain active

#### Scenario: Disable MC QoS
- **WHEN** MC QoS is disabled for a PARTID
- **THEN** its configured QoS is retained but its base arbitration QoS is zero

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

### Requirement: Configurable MC Scheduling Constants
The memory-controller model SHALL expose token bucket window, aging quantum,
aging step cap, BMIN QoS promotion, and soft-limit QoS demotion as
validated configuration fields.

#### Scenario: Change BMIN preference strength
- **WHEN** the configured BMIN QoS promotion is increased
- **THEN** under-BMIN candidates receive the new bounded promotion without source changes

#### Scenario: Change soft-limit penalty strength
- **WHEN** the configured soft-limit QoS demotion is increased
- **THEN** over-BMAX candidates lose the new bounded number of levels only while contended

### Requirement: Control Algorithm Evidence
The memory-controller monitor SHALL report the algorithm parameters and
per-PARTID BMIN-credit, soft-limit, hard-block, and throttle evidence needed
to validate scheduling behavior.

#### Scenario: Inspect a controlled interval
- **WHEN** BMIN or BMAX affects request selection
- **THEN** monitor output identifies the configured QoS constants, base and effective QoS, and affected request counters

### Requirement: 3-bit QoS Arbitration
The MC scheduler SHALL choose the highest effective QoS candidate and SHALL
choose the oldest request when effective QoS values are equal.

#### Scenario: Clamp QoS adjustments
- **WHEN** aging, BMIN promotion, or soft demotion changes QoS
- **THEN** effective QoS remains within zero through seven

#### Scenario: Hard limit blocks a high-QoS request
- **WHEN** a QoS-seven hard-limited request lacks tokens
- **THEN** it is excluded from arbitration until tokens are available
