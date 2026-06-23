## MODIFIED Requirements

### Requirement: MC带宽监控累计计数器

MC MUST 为每个PARTID维护63-bit累计服务字节监控计数器，并在监控边界使用累计差分计算sample bandwidth。

#### Scenario: 周期差分

- **WHEN** MC监控边界到达
- **THEN** `delta_bytes` MUST 等于当前63-bit累计计数和上一采样累计计数的模差值
- **AND** `sample_bandwidth` MUST 由`delta_bytes * 8 / monitor_period_ns`计算

### Requirement: MC滤波带宽控制输入

MC BMIN/BMAX/QoS/CBusy带宽项 MUST 使用权重和为1的filtered bandwidth作为新控制周期的control input。

#### Scenario: 计算并生效

- **WHEN** 周期k结束并得到`sample_bandwidth[k]`
- **THEN** `filtered_bandwidth[k] = history_weight * filtered_bandwidth[k-1] + current_weight * sample_bandwidth[k]`
- **AND** `history_weight + current_weight` MUST 等于1
- **AND** `filtered_bandwidth[k]` MUST 作为周期k+1的`control_bandwidth`
