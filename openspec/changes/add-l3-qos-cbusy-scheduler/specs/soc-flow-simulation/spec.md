## MODIFIED Requirements

### Requirement: P1三条闭环场景

P1 MUST 跑通L3 CMAX occupancy control、MC BMAX bandwidth control和
CBusy -> RN OSTD source throttling三条场景。P1之后允许新增L3本地QoS调度作为辅助MC带宽控制的普通机制，
但不得新增P1专用数据面、UI通路或validation stage。

#### Scenario: L3 CMAX occupancy control

- **WHEN** L3发布并保存的control sampled occupancy达到或超过CMAX
- **THEN** 在对应`action_effective_time_ns`之后，该PARTID新增L3 allocation MUST 被限制、旁路或只能自替换
- **AND** actual occupancy MAY 因在途fill、采样误差或交织误差短暂过冲

#### Scenario: MC BMAX bandwidth control

- **WHEN** MC基于63bit累计计数差分发布并保存的control bandwidth超过BMAX
- **THEN** soft BMAX MUST 能改变对应PARTID的MC effective QoS
- **AND** hard BMAX MUST 能产生对应PARTID的hard block
- **AND** 事件 MUST 标明`limit_mode=soft`或`limit_mode=hard`

#### Scenario: CBusy返回RN后源端限流

- **WHEN** MC在完成服务时把CBusy状态采样到RSP或DAT返回旁带
- **THEN** RN收到返回后 MUST 能按该返回事务归因出的PARTID降低effective OSTD
- **AND** 目标MC MUST 只作为反馈来源、路由和诊断字段，不得作为RN源端限流索引
- **AND** 不得影响其他PARTID的effective OSTD
