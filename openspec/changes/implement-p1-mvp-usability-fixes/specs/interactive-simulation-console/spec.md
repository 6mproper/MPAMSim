## MODIFIED Requirements

### Requirement: P0控制验证展示

控制台 MUST 将P0验证展示为机制生效证据，而不是目标达成证明。

#### Scenario: 查看控制验证

- **WHEN** 控制台显示PARTID、控制事件、图例、预设说明或矩阵条目
- **THEN** PARTID编号 MUST 显示为`PARTID N`或明确等价的紧凑标签`ID N`
- **AND** MUST NOT 使用`P0`、`P1`、`P2`指代PARTID
