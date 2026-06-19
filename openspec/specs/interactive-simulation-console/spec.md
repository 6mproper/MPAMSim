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
