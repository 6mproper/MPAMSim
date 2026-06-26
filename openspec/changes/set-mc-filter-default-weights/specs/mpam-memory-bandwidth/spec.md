## MODIFIED Requirements

### Requirement: 63bit累计计数驱动BMIN和BMAX

MC MUST 为每个PARTID维护63bit累计服务字节计数。每个本地监控边界基于累计计数差分计算上一个窗口的采样带宽，
再用可配权重计算filtered bandwidth，并把该filtered bandwidth保存为后续控制窗口的control bandwidth。
BMIN/BMAX不得读取当前瞬时服务字节或actual/debug带宽。默认MC滤波权重 MUST 为
`history_weight=0.95`、`current_weight=0.05`，用于降低短窗口raw带宽量化噪声；用户仍可配置这两个权重。

#### Scenario: 累计计数差分

- **WHEN** MC运行到监控边界T
- **THEN** MUST 保存当前63bit累计计数
- **AND** MUST 用`(cumulative[T] - cumulative[T-1]) mod 2^63`计算本窗口服务字节
- **AND** MUST 用该差分计算`sample_bandwidth`

#### Scenario: 权重滤波

- **WHEN** MC计算本窗口`sample_bandwidth`
- **THEN** `filtered_bandwidth[T] = history_weight * filtered_bandwidth[T-1] + current_weight * sample_bandwidth[T]`
- **AND** `history_weight + current_weight` MUST 等于1
- **AND** 默认权重 MUST 为`0.95/0.05`
- **AND** `filtered_bandwidth[T]` MUST 保存为后续控制窗口的`control_bandwidth`
