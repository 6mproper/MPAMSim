## ADDED Requirements

### Requirement: Mechanism Verification Workloads
The simulator SHALL support deterministic built-in workloads that isolate
cache minimum/maximum allocation and memory bandwidth minimum/maximum behavior.

#### Scenario: Repeat a verification suite
- **WHEN** the same parameters and seed are submitted twice
- **THEN** every verification check and measured evidence is identical
