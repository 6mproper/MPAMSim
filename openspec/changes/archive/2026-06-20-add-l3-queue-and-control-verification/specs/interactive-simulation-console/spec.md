## ADDED Requirements

### Requirement: Flow-Control Algorithm Configuration
The console SHALL configure L3 queue depth and lookup parallelism plus MC token
window, aging, BMIN boost, soft-limit penalty, and aging cap.

#### Scenario: Edit an algorithm parameter
- **WHEN** the operator changes a supported algorithm parameter
- **THEN** the submitted validated configuration and monitor snapshots use the new value

### Requirement: Built-In Control Verification
The console SHALL run deterministic CMIN, CMAX, BMIN, BMAX soft-limit, and
BMAX hard-limit microbenchmarks and SHALL display explicit checks and evidence.

#### Scenario: Run the control verification suite
- **WHEN** the operator starts algorithm verification
- **THEN** the cases execute sequentially and each mechanism reports pass/fail, expected behavior, and measured evidence
