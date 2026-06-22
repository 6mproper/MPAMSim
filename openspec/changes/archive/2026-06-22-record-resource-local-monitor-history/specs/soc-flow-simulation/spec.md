## MODIFIED Requirements

### Requirement: 每PARTID CPU OSTD监控

仿真器 MUST 在每个控制周期采样requester的PARTID OSTD，且不引入CPU流水线模型。
每个L3和MC本地监控周期 MUST 发布所有16个PARTID的离散periodic state sample，
包括disabled和0活动PARTID。

#### Scenario: 采样OSTD

- **WHEN** 捕获控制周期
- **THEN** 每个requester/PARTID报告当前值、周期峰值、配置上限、issued/completed和backpressure

#### Scenario: 重置周期峰值

- **WHEN** 一个CPU监控周期结束
- **THEN** 下一周期峰值从当前OSTD开始

#### Scenario: 每本地周期离散采样所有PARTID

- **WHEN** L3或MC完成一个本地监控周期
- **THEN** 16个PARTID的current、raw、filtered、configured和state值作为离散samples保存

#### Scenario: disabled PARTID标记

- **WHEN** PARTID未被任何workload使用
- **THEN** 采样值使用null，semantic标记为control_state，不伪装为0

## ADDED Requirements

### Requirement: 因果监控链稳定ID

每个监控sample MUST 使用全局唯一的`observation_id`（基于resource_id和local_cycle）。
控制决策 MUST 引用触发它的`observation_id`。控制事件 MUST 保存`decision_id`、
`action_id`和可选`cause_id`以形成完整的observation→decision→action→effect因果链。

#### Scenario: 慢速策略后续观测

- **WHEN** policy根据observation O1做出decision D1并触发action A1
- **THEN** A1生效后的下一次observation O2 MUST 关联`cause_id=A1`以建立因果链

#### Scenario: 相同seed确定性ID

- **WHEN** 两次仿真使用相同配置和seed
- **THEN** 所有observation_id、decision_id和action_id序列完全一致
