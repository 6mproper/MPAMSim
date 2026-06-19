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
