## ADDED Requirements

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
