## ADDED Requirements

### Requirement: Resource-Oriented PARTID Monitoring
The interactive console SHALL provide CPU, L3, and memory-controller resource views that aggregate the selected control-interval snapshot by PARTID.

#### Scenario: Inspect CPU state
- **WHEN** the operator selects the CPU resource view
- **THEN** each visible PARTID reports requester mapping, current and interval-peak outstanding requests, configured outstanding capacity, issued/completed requests, and requester backpressure

#### Scenario: Inspect L3 state
- **WHEN** the operator selects the L3 resource view
- **THEN** each visible PARTID reports sampled bandwidth, estimated occupancy/utilization, hit rate, allocation denials, and effective CMIN/CMAX/CPBM controls

#### Scenario: Inspect memory-controller state
- **WHEN** the operator selects the MC resource view
- **THEN** each visible PARTID reports achieved bandwidth/utilization, requests, queue and throttle delay, effective BMIN/BMAX/mode/priority, and limit events

### Requirement: Independent PARTID Visibility
The interactive console SHALL expose independent visibility selection for all 16 PARTIDs and SHALL use that selection for resource rows and per-PARTID trend/detail views.

#### Scenario: Select a subset
- **WHEN** the operator enables PARTID 2 and PARTID 7 and disables all others
- **THEN** the resource table and per-PARTID chart series show only PARTID 2 and PARTID 7

#### Scenario: Clear the selection
- **WHEN** the operator clears all PARTID visibility toggles
- **THEN** the console shows an explicit no-selection state without changing the simulation configuration

### Requirement: Feedback-Control Status
The interactive console SHALL show the feedback-control state for each visible PARTID at the selected simulation time.

#### Scenario: Closed-loop update exists
- **WHEN** a closed-loop control update has been applied to a visible PARTID
- **THEN** the dashboard identifies the PARTID as adjusted and shows the latest update time, target, field, and reason

#### Scenario: No runtime update exists
- **WHEN** no control update exists for a visible PARTID
- **THEN** the dashboard distinguishes no-control, static-control, and closed-loop monitoring states
