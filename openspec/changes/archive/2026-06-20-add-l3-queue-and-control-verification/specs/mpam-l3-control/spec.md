## ADDED Requirements

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
