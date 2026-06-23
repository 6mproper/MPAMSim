## ADDED Requirements

### Requirement: P1最小闭环MVP范围

P1 MUST 实现最小闭环MVP，不得扩展为完整SoC仿真。

#### Scenario: P1范围确认

- **WHEN** 规划、实现或验收P1
- **THEN** MUST 聚焦L3 CMAX、MC BMAX和CBusy到RN OSTD三条闭环
- **AND** MUST NOT 把NoC QoS、credit/VC、完整DRAM bank/row/refresh、完整resctrl/libvirt接口、完整UI工作区、自动根因分类、PPA综合评分或所有控制组合测试纳入P1完成条件

### Requirement: P1复用常规数据面和证据链

P1 MUST 复用现有类型化`Transaction`、`MonitorSample`、`ControlEvent`和决策轨迹类型。
当前实现中的决策轨迹类型名为`ControlDecision`；UI或文档可以称为`DecisionTrace`，
但不得新增另一套P1专用决策类型。

#### Scenario: 不新增阶段旁路

- **WHEN** P1场景运行或展示结果
- **THEN** MUST 使用常规仿真模式、常规数据模型和常规UI通路
- **AND** MUST NOT 新增`validation_stage`运行模式、P1专用数据面或P1专用UI通路

#### Scenario: 控制器输入隔离

- **WHEN** P1中的CMAX、BMAX或CBusy相关控制器做决策
- **THEN** MUST 只读取规格授权的监控值、本地执行状态和配置状态
- **AND** MUST NOT 读取actual语义数据作为控制输入

### Requirement: P1三条闭环场景

P1 MUST 跑通L3 CMAX occupancy control、MC BMAX bandwidth control和
CBusy -> RN OSTD source throttling三条场景。

#### Scenario: L3 CMAX occupancy control

- **WHEN** 上一发布filtered sampled occupancy达到或超过CMAX
- **THEN** 在对应`action_effective_time_ns`之后，该PARTID新增L3 allocation MUST 被限制、旁路或只能自替换
- **AND** actual occupancy MAY 因在途fill、采样误差或交织误差短暂过冲

#### Scenario: MC BMAX bandwidth control

- **WHEN** 上一发布filtered bandwidth超过BMAX
- **THEN** soft BMAX MUST 能改变对应PARTID的MC effective QoS
- **AND** hard BMAX MUST 能产生对应PARTID的hard block
- **AND** 事件 MUST 标明`limit_mode=soft`或`limit_mode=hard`

#### Scenario: CBusy返回RN后源端限流

- **WHEN** MC在完成服务时把CBusy状态采样到RSP或DAT返回旁带
- **THEN** RN收到返回后 MUST 降低对应`(MC, PARTID)`的effective OSTD
- **AND** 不得影响其他MC或其他PARTID的effective OSTD

### Requirement: P1成功标准

P1成功 MUST 以控制动作闭环和证据完整性判断，不得要求任意目标必然达成。

#### Scenario: 确定性复现

- **WHEN** 两次运行使用相同配置和seed
- **THEN** 三条P1场景的关键监控、决策、控制事件和结果指标 MUST 确定性复现

#### Scenario: 因果ID完整

- **WHEN** P1导出任一控制事件
- **THEN** 该事件 MUST 能追踪`monitor_sample_id`、`decision_id`和`action_effective_time_ns`

#### Scenario: 控制结果失败不中止

- **WHEN** P1场景出现目标未达、过冲、振荡、控制饱和或不可行目标
- **THEN** MUST 记录为`CONTROL_OUTCOME`
- **AND** MUST NOT 中止仿真
