## ADDED Requirements

### Requirement: CPU Outstanding Monitor By PARTID
The simulator SHALL sample requester outstanding state by PARTID at every control interval without introducing a CPU pipeline model.

#### Scenario: Capture outstanding state
- **WHEN** a control interval is captured
- **THEN** each configured requester/PARTID mapping reports current outstanding, interval peak outstanding, configured maximum outstanding, cumulative issued/completed requests, and cumulative requester backpressure

#### Scenario: Reset interval peak
- **WHEN** one CPU monitor interval is completed
- **THEN** the next interval peak starts from the current outstanding state rather than retaining the previous interval peak
