## ADDED Requirements

### Requirement: 阶段命名与PARTID命名消歧

规格、OpenSpec change、测试说明和UI文案 MUST 明确区分阶段命名与MPAM PARTID命名。

#### Scenario: 描述阶段验收

- **WHEN** 文档描述机制可信性、后续增强阶段或计划优先级
- **THEN** 可以使用`P0`、`P1`、`P2`等阶段命名
- **AND** 首次出现时 SHOULD 说明它表示阶段、验收或计划优先级

#### Scenario: 描述MPAM标识

- **WHEN** 文档、测试或UI文案描述MPAM PARTID编号
- **THEN** MUST 写成`PARTID 0`、`PARTID 1`、`PARTID 2`或`PARTID N`
- **AND** MUST NOT 使用`P0`、`P1`、`P2`缩写PARTID
