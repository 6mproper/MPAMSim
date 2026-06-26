## ADDED Requirements

### Requirement: P0/P1监控控制时序门槛

P0/P1阶段 MUST 先冻结监控、滤波、控制和动作之间的时序语义，不得新增阶段专用仿真模式、
数据模型或UI通路；该门槛不是独立的后续仿真模式。

#### Scenario: 监控边界非偷跑顺序

- **WHEN** 任一MSC到达本地监控边界
- **THEN** 控制器 MUST 先关闭刚结束窗口并读取授权监控样本
- **AND** MUST 保存新的control input供后续控制窗口读取
- **AND** 窗口内尚未发布的raw、actual或debug状态 MUST NOT 驱动控制动作

#### Scenario: 控制动作可追踪

- **WHEN** 控制动作由monitor-driven decision产生
- **THEN** 证据 MUST 能区分UI/导出显示的最新发布filtered监控值和控制器实际读取的control input
- **AND** `action_effective_time_ns` MUST 不早于control input被锁存的本地监控边界

#### Scenario: 无阶段旁路

- **WHEN** 运行P0/P1相关微测试、控制验证或普通仿真
- **THEN** MUST 复用常规`Transaction`、`MonitorSample`、`ControlEvent`和控制总览/因果链UI通路
- **AND** MUST NOT 新增`validation_stage`或阶段专用数据面
