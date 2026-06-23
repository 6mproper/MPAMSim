## ADDED Requirements

### Requirement: P0 P1时序前置门槛

监控、滤波、控制和动作的双缓冲时序 MUST 作为P0机制可信和P1最小闭环的共同前置门槛。

#### Scenario: P0时序门槛

- **WHEN** P0验证控制机制是否可信
- **THEN** MUST 验证控制器读取的是锁存`control_input`
- **AND** MUST 验证同一监控边界刚发布的`filtered_monitor`不会立即驱动控制

#### Scenario: P1闭环门槛

- **WHEN** P1验证L3 CMAX、MC BMAX或CBusy闭环
- **THEN** 控制事件 MUST 引用锁存`control_input`对应的monitor sample
- **AND** `action_effective_time_ns` MUST 不早于该control input被锁存的本地边界

### Requirement: 四层监控语义

平台telemetry MUST 区分`actual`、`raw_monitor`、`filtered_monitor`和`control_input`。

#### Scenario: control input语义

- **WHEN** L3或MC导出控制器实际读取的锁存监控值
- **THEN** 对应`MonitorSample.semantic` MUST 为`control_input`
- **AND** MUST NOT 被归类为`actual`或`filtered_monitor`

#### Scenario: latest filtered语义

- **WHEN** L3或MC导出刚发布的滤波监控值
- **THEN** 对应`MonitorSample.semantic` MUST 为`filtered_monitor`
- **AND** UI MUST 标注为latest filtered或最新发布监控值

### Requirement: 控制结果契约

目标未达、过冲、饱和、不可行或性能恶化 MUST 记录为控制结果，而不是仿真失败。

#### Scenario: CONTROL_OUTCOME字段

- **WHEN** 导出任一控制事件
- **THEN** 事件行 SHOULD 包含稳定的`outcome_state`和`outcome_reason`字段
- **AND** outcome状态 MUST 用于解释目标偏离，不得作为自动中止条件

### Requirement: 控制上下文扩展边界

后续新增控制能力 MUST 通过类型化`ControlContext`读取授权监控样本、资源scope、
上一控制状态和动作生效边界；P1不因此扩展到完整SoC仿真。

#### Scenario: 新控制策略

- **WHEN** 新增NoC QoS、PE侧限流、多MC协同或PMG策略
- **THEN** SHOULD 通过`ControlContext`声明授权输入
- **AND** MUST NOT 直接读取私有actual状态或阶段专用数据面
