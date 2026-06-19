## ADDED Requirements

### Requirement: Sixteen PARTID cache settings
Each configured L3/SLC MSC SHALL expose independent settings and monitoring entries for exactly 16 PARTIDs numbered 0 through 15.

#### Scenario: Inspect an idle PARTID
- **WHEN** a configured PARTID generates no requests during an interval
- **THEN** its L3 monitor row remains present with zero activity counters

### Requirement: L3 allocation controls
The L3 model SHALL apply CPBM as the eligible-way mask, CMAX as the maximum sampled ways allocated to a PARTID, and CMIN as sampled ownership protected from replacement.

#### Scenario: Restrict cache allocation
- **WHEN** a PARTID has fewer CPBM-enabled ways or a lower CMAX
- **THEN** its allowed capacity and sampled allocation cannot exceed the configured limit

#### Scenario: Protect minimum allocation
- **WHEN** a victim PARTID owns no more sampled ways than its CMIN
- **THEN** another PARTID cannot evict those protected sampled ways

### Requirement: One-in-eight-set approximate monitor
The L3 model SHALL sample the first set in every group of eight sets and SHALL scale sampled access and occupancy observations by eight.

#### Scenario: Access a sampled set
- **WHEN** a request maps to a set whose index modulo eight is zero
- **THEN** the model updates sampled per-way PARTID ownership and sampled traffic counters

#### Scenario: Access a non-sampled set
- **WHEN** a request maps to any other set in the eight-set group
- **THEN** the model does not allocate sampled tag or way state for that access

### Requirement: Control-disabled monitoring
The no-control policy SHALL preserve all 16 monitor entries while reporting unrestricted effective cache settings.

#### Scenario: Run without MPAM enforcement
- **WHEN** the selected policy is `no_control`
- **THEN** CPBM, CMIN, and CMAX do not restrict allocation, but all PARTID monitor rows remain available
