## ADDED Requirements

### Requirement: Target And Effect Evidence
The simulator SHALL emit interval evidence sufficient to compare configured
cache, bandwidth, QoS, and latency targets with achieved values and control
cost per PARTID.

#### Scenario: Evaluate a complete run
- **WHEN** a simulation completes
- **THEN** target adherence can be calculated from interval snapshots without inferring missing internal state from final averages
