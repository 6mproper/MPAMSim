# soc-flow-simulation Specification

## Purpose
Define the deterministic system-level simulation path, configuration boundary,
latency attribution, and reproducible output contract.
## Requirements
### Requirement: Deterministic system-level simulation
The system SHALL execute a discrete-event SoC model deterministically when configuration and random seed are unchanged.

#### Scenario: Repeat an identical run
- **WHEN** two simulations use the same validated configuration and seed
- **THEN** their issued requests, completed requests, and reported metrics are identical

### Requirement: Configurable multicore request path
The system SHALL model configurable cores, threads, requesters, NoC transport, shared L3/SLC instances, and memory controllers as a causal request path.

#### Scenario: Increase active requesters
- **WHEN** a workload uses per-requester injection and the active requester count increases
- **THEN** offered traffic and shared-resource contention increase without requiring source-code changes

### Requirement: Flow-control delay attribution
The system SHALL attribute completed-request latency to NoC, cache, memory queue, memory service, and throttle components.

#### Scenario: Diagnose a bandwidth cap
- **WHEN** a hard memory bandwidth limit delays requests
- **THEN** the exported metrics report throttle delay separately from queue and service delay

### Requirement: Reproducible outputs
The system SHALL export resolved configuration, topology, run summary, per-PARTID metrics, per-MSC metrics, timeline traces, and control traces.

#### Scenario: Complete a simulation run
- **WHEN** a simulation finishes with output enabled
- **THEN** machine-readable JSON and CSV artifacts and an optional static HTML report are generated

### Requirement: Independent hardware-thread workloads
The web configuration builder SHALL generate one workload for every enabled row in the 16-thread stimulus matrix and SHALL bind it to the row's fixed requester.

#### Scenario: Enable every stimulus
- **WHEN** all 16 stimulus rows are enabled
- **THEN** the resolved configuration contains 16 workloads bound to 16 distinct CPU-thread requesters

#### Scenario: Disable one stimulus
- **WHEN** one stimulus row is disabled
- **THEN** no workload is generated for that requester and the remaining requester mappings are unchanged

### Requirement: Validated stimulus workload
Every enabled stimulus SHALL produce exactly one injection-rate field and SHALL satisfy PARTID, PMG, request-size, read-ratio, working-set, and target validation.

#### Scenario: Select MRPS
- **WHEN** a row uses the MRPS rate unit
- **THEN** the workload contains `injection_rate_mrps` and omits `injection_rate_gbps`

#### Scenario: Select Gbps
- **WHEN** a row uses the Gbps rate unit
- **THEN** the workload contains `injection_rate_gbps` and omits `injection_rate_mrps`

### Requirement: Aggregate web-job safety
The builder SHALL estimate offered requests across all enabled thread stimuli and SHALL reject configurations above the web-job request limit.

#### Scenario: Excessive combined traffic
- **WHEN** the sum of estimated requests from enabled rows exceeds two million
- **THEN** configuration validation rejects the job before simulation starts
