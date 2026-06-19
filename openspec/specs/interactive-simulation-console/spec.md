# interactive-simulation-console Specification

## Purpose
Define the local user interface for configuring, running, observing, and
reporting SoC flow-control and MPAM simulations.
## Requirements
### Requirement: Direct configuration
The local web console SHALL allow users to configure SoC topology, multicore stimulus, simulation timing, flow-control policy, and all 16 PARTID control rows without editing source files.

#### Scenario: Configure a non-default PARTID
- **WHEN** a user selects arbitrary protected and background PARTIDs and edits their controls
- **THEN** the submitted simulation uses those PARTIDs and settings in the validated common configuration schema

### Requirement: Dynamic simulation execution
The local web console SHALL start simulations as background jobs and SHALL update progress and interval results while a run is active.

#### Scenario: Run from the interface
- **WHEN** the user activates the run command with valid parameters
- **THEN** the interface transitions through running state to done or failed state and remains responsive

### Requirement: MPAM result visualization
The console SHALL display per-PARTID latency and bandwidth, per-MSC queue occupancy, delay attribution, control updates, and a 16-row MPAM monitor table.

#### Scenario: Inspect MPAM results
- **WHEN** a simulation completes
- **THEN** the MPAM monitor view contains one row for every PARTID and shows L3 sampled estimates plus memory-controller bandwidth-control events

### Requirement: Report access
The console SHALL provide access to the static report generated from the same completed simulation job.

#### Scenario: Open a completed report
- **WHEN** a job completes successfully
- **THEN** the interface exposes a link to that job's generated HTML report

### Requirement: Sixteen-thread stimulus editor
The interactive console SHALL display exactly 16 stimulus rows mapped one-to-one to the hardware-thread requesters of an eight-core, two-thread topology.

#### Scenario: Inspect requester mapping
- **WHEN** the stimulus editor is initialized
- **THEN** its rows identify `cpu0.t0`, `cpu0.t1`, through `cpu7.t1` exactly once each

### Requirement: Per-thread stimulus controls
Each stimulus row SHALL configure enable state, PARTID, PMG, workload type, injection rate, rate unit, request size, read ratio, working-set size, and optional P99 target.

#### Scenario: Configure a thread independently
- **WHEN** a user changes the PARTID, PMG, traffic type, or rate of one row
- **THEN** no other thread row is implicitly modified

### Requirement: Stable interactive topology
The interactive reference scenario SHALL use eight cores and two threads per core while the generic YAML and Python interfaces remain topology-configurable.

#### Scenario: Load web defaults
- **WHEN** the console loads its default parameters
- **THEN** it reports eight cores, two threads per core, and 16 thread stimulus rows

### Requirement: Contextual configuration help
The interactive console SHALL provide concise explanations for configuration categories, fields, table columns, policy choices, result categories, and abbreviated MPAM terms through pointer hover and keyboard focus.

#### Scenario: Inspect a field explanation
- **WHEN** a user hovers over or focuses a supported configuration label or table control
- **THEN** a tooltip explains its unit, behavior, or modeling meaning without changing the configured value

### Requirement: Stimulus type comparison
The stimulus Type control SHALL explain the behavioral distinction among stream, pointer chase, random read, mixed read/write, and burst traffic.

#### Scenario: Inspect the Type control
- **WHEN** a user hovers over or focuses a stimulus Type selector
- **THEN** the tooltip lists the locality, address, and burst characteristics of every supported type

### Requirement: Live monitor-group view
The console SHALL display the latest software-visible values for every configured `(PARTID, PMG)` monitor group and SHALL update them at simulation control intervals.

#### Scenario: Observe a running simulation
- **WHEN** a control-interval snapshot is received
- **THEN** the monitor-group table updates L3 estimated occupancy/utilization and MC bandwidth/utilization without waiting for final export

#### Scenario: Inspect an idle group
- **WHEN** a configured stimulus group has no activity in the latest interval
- **THEN** its row remains visible with zero activity values

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

### Requirement: Per-Control Switches
The interactive PARTID editor SHALL expose independent switches for CPBM, CMIN, CMAX, BMIN, BMAX, priority, and CBusy.

#### Scenario: Disable one mechanism
- **WHEN** the operator disables one control switch
- **THEN** its configured value remains visible but the result monitor reports that mechanism as disabled and shows its neutral effective value

### Requirement: CBusy Configuration And Evidence
The console SHALL configure CBusy timing/threshold parameters and per-level OSTD caps and SHALL display the resulting feedback evidence.

#### Scenario: Observe CBusy feedback
- **WHEN** an MC raises CBusy for a selected PARTID
- **THEN** the MC view shows detector level/inputs and the CPU view shows the matching effective OSTD and CBusy stall

#### Scenario: Compare mechanisms
- **WHEN** runs differ only in BMAX and CBusy enable switches
- **THEN** exported and live metrics are sufficient to compare queueing, latency, throughput, source stall, and control transitions
