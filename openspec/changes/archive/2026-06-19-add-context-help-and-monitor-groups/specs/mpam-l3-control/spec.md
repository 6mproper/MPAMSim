## ADDED Requirements

### Requirement: PMG-scoped sampled cache monitoring
The L3 monitor SHALL attribute sampled traffic and sampled way ownership to `(PARTID, PMG)` monitor groups while retaining PARTID-only cache controls.

#### Scenario: Allocate a sampled cache line
- **WHEN** a miss from a request with PARTID P and PMG G allocates a sampled way
- **THEN** the sampled way records P and G for occupancy attribution

#### Scenario: Report group occupancy
- **WHEN** a cache interval snapshot is captured
- **THEN** each active monitor group reports sampled requests, estimated access bandwidth, estimated occupancy bytes, allowed PARTID capacity, and estimated occupancy utilization
