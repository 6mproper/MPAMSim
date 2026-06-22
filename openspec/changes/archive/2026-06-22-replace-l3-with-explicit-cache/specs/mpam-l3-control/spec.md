## ADDED Requirements

### Requirement: 控制与监控共享真实Line状态

CPBM、CMIN、CMAX、实际占用和1/8抽样监控 MUST 基于同一组真实L3 line，不得维护独立
owner影子作为控制事实。

#### Scenario: 非抽样Set分配

- **WHEN** PARTID在非抽样set完成fill
- **THEN** actual occupancy增加而本次sampled occupancy可以不增加

#### Scenario: 抽样Set分配

- **WHEN** PARTID在`set % 8 == 0`的set完成fill
- **THEN** actual和sampled owner都来自同一line的owner字段
