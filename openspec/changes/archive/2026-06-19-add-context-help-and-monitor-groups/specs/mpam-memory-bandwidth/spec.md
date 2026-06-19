## ADDED Requirements

### Requirement: PMG-scoped memory bandwidth monitoring
The memory-controller monitor SHALL attribute serviced requests and bytes to `(PARTID, PMG)` monitor groups while retaining PARTID-only bandwidth enforcement.

#### Scenario: Service a monitor-group request
- **WHEN** the memory controller dispatches a request with PARTID P and PMG G
- **THEN** the corresponding group counters record requests, bytes, queue delay, service delay, and applicable limit events

#### Scenario: Report group bandwidth utilization
- **WHEN** a memory-controller interval snapshot is captured
- **THEN** each active monitor group reports achieved bandwidth and utilization relative to that controller's total modeled bandwidth
