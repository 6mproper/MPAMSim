## ADDED Requirements

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
