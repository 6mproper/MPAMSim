# mpam-memory-bandwidth Specification

## Purpose
Define per-memory-controller, per-PARTID bandwidth reservation, limiting,
scheduling, and monitoring behavior.

## Requirements
### Requirement: Sixteen PARTID memory settings
Each memory-controller MSC SHALL expose independent bandwidth settings, token state, priority, and monitoring entries for exactly 16 PARTIDs numbered 0 through 15.

#### Scenario: Multiple memory controllers
- **WHEN** the SoC has more than one memory controller
- **THEN** each controller maintains independent per-PARTID BMIN and BMAX behavior

### Requirement: BMAX hard limit
The memory-controller model SHALL implement hard BMAX as a per-PARTID token bucket that blocks dispatch until sufficient tokens exist.

#### Scenario: Exceed a hard limit
- **WHEN** a queued request lacks BMAX tokens in `hardlimit` mode
- **THEN** dispatch waits, throttle delay increases, and a hard-limit block event is monitored

### Requirement: BMAX soft limit
The memory-controller model SHALL keep `softlimit` traffic eligible and SHALL apply an over-limit scheduling penalty only while requests contend.

#### Scenario: Uncontended soft-limit traffic
- **WHEN** a PARTID exceeds BMAX but no other request is contending
- **THEN** the controller remains work-conserving and dispatches the request

#### Scenario: Contended soft-limit traffic
- **WHEN** a PARTID exceeds BMAX while another request is eligible
- **THEN** the over-limit request receives a lower effective scheduling priority

### Requirement: BMIN reservation approximation
The memory-controller scheduler SHALL grant an effective-priority bonus to a PARTID that has available BMIN credit.

#### Scenario: Compete below BMIN
- **WHEN** multiple PARTIDs contend and one request is backed by BMIN credit
- **THEN** that request receives the configured reservation-oriented scheduler preference

### Requirement: Bandwidth monitoring
The memory-controller monitor SHALL report achieved bandwidth, configured BMIN and BMAX, limit mode, priority, queue delay, service delay, throttle delay, soft-limit requests, and hard-limit block events per PARTID.

#### Scenario: Display aggregate results
- **WHEN** the interactive console combines multiple memory-controller snapshots
- **THEN** aggregate bandwidth and configured limits are labeled as sums across controller instances
