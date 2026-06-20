# mpam-l3-control Specification

## Purpose
Define 16-PARTID L3/SLC allocation controls and the bounded-cost approximate
set/way monitor used for system architecture exploration.
## Requirements
### Requirement: Sixteen PARTID cache settings
Each configured L3/SLC MSC SHALL expose independent settings and monitoring entries for exactly 16 PARTIDs numbered 0 through 15.

#### Scenario: Inspect an idle PARTID
- **WHEN** a configured PARTID generates no requests during an interval
- **THEN** its L3 monitor row remains present with zero activity counters

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

### Requirement: One-in-eight-set approximate monitor
The L3 model SHALL sample the first set in every group of eight sets and SHALL scale sampled access and occupancy observations by eight.

#### Scenario: Access a sampled set
- **WHEN** a request maps to a set whose index modulo eight is zero
- **THEN** the model updates sampled per-way PARTID ownership and sampled traffic counters

#### Scenario: Access a non-sampled set
- **WHEN** a request maps to any other set in the eight-set group
- **THEN** the model does not allocate sampled tag or way state for that access

### Requirement: Control-disabled monitoring
The no-control policy SHALL preserve all 16 monitor entries while reporting unrestricted effective cache settings.

#### Scenario: Run without MPAM enforcement
- **WHEN** the selected policy is `no_control`
- **THEN** CPBM, CMIN, and CMAX do not restrict allocation, but all PARTID monitor rows remain available

### Requirement: PMG-scoped sampled cache monitoring
The L3 monitor SHALL attribute sampled traffic and sampled way ownership to `(PARTID, PMG)` monitor groups while retaining PARTID-only cache controls.

#### Scenario: Allocate a sampled cache line
- **WHEN** a miss from a request with PARTID P and PMG G allocates a sampled way
- **THEN** the sampled way records P and G for occupancy attribution

#### Scenario: Report group occupancy
- **WHEN** a cache interval snapshot is captured
- **THEN** each active monitor group reports sampled requests, estimated access bandwidth, estimated occupancy bytes, allowed PARTID capacity, and estimated occupancy utilization

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

### Requirement: Bounded L3 Request Queue
Each L3/SLC MSC SHALL admit requests through a configurable bounded FIFO queue
and SHALL execute no more than the configured lookup parallelism concurrently.

#### Scenario: L3 queue has capacity
- **WHEN** a request arrives and a queue entry is available
- **THEN** it is admitted, waits for a lookup slot, and records its queue delay

#### Scenario: L3 queue is full
- **WHEN** a request arrives while the bounded queue is full
- **THEN** it retries later and accumulates L3 admission backpressure

### Requirement: L3 Queue Monitoring
The L3 monitor SHALL report configured queue depth, lookup parallelism,
average and peak queue occupancy, active lookups, queue delay, admission
backpressure, and queue-full events.

#### Scenario: Observe L3 pressure
- **WHEN** offered lookup concurrency exceeds available lookup slots
- **THEN** queue occupancy and queue delay become non-zero

### Requirement: CMIN-Aware Growth Below CMAX
A PARTID below CMAX SHALL be allowed to replace an eligible global LRU victim
whose owner remains above CMIN.

#### Scenario: Aggressor competes with protected owner
- **WHEN** an aggressor is below CMAX and the victim owner is at CMIN
- **THEN** that victim is skipped and another eligible owner above CMIN is selected

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
