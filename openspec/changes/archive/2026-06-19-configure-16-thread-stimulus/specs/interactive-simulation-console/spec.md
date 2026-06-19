## ADDED Requirements

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
