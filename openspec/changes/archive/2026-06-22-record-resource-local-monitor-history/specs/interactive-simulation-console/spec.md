## ADDED Requirements

### Requirement: 离散本地采样证据显示

Web控制台 MUST 支持按resource_id、PARTID和时间范围过滤离散本地监控samples，
并用颜色区分semantic（actual、raw_monitor、filtered_monitor、control_state、configured_target）。

#### Scenario: 单PARTID离散采样查看

- **WHEN** 用户选择MC0和PARTID 3
- **THEN** 显示该PARTID全部本地周期的raw、filtered、target和state时间序列点

#### Scenario: disabled PARTID不显示

- **WHEN** PARTID在整个仿真中未被配置
- **THEN** Web默认隐藏该PARTID，可手动显示
