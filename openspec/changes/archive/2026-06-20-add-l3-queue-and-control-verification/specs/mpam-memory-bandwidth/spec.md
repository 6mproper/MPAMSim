## ADDED Requirements

### Requirement: Configurable MC Scheduling Constants
The memory-controller model SHALL expose token bucket window, aging quantum,
aging bonus cap, BMIN priority boost, and soft-limit priority penalty as
validated configuration fields.

#### Scenario: Change BMIN preference strength
- **WHEN** the configured BMIN priority boost is increased
- **THEN** under-BMIN candidates receive the new boost without source changes

#### Scenario: Change soft-limit penalty strength
- **WHEN** the configured soft-limit penalty is increased
- **THEN** over-BMAX candidates lose the new amount only while contended

### Requirement: Control Algorithm Evidence
The memory-controller monitor SHALL report the algorithm parameters and
per-PARTID BMIN-credit, soft-limit, hard-block, and throttle evidence needed
to validate scheduling behavior.

#### Scenario: Inspect a controlled interval
- **WHEN** BMIN or BMAX affects request selection
- **THEN** monitor output identifies the configured constants and affected request counters
