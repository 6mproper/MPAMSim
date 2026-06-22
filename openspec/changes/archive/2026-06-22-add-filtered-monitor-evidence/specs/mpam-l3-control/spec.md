## ADDED Requirements

### Requirement: L3本地周期MPAM监控

L3 MUST 每个可配本地监控周期发布所有PARTID的raw抽样owner、filtered owner和抽样访问带宽。

#### Scenario: 256拍发布

- **WHEN** L3运行到一个监控周期边界
- **THEN** raw读取每8个set首set的way owner，filtered按可配权重更新

### Requirement: CMIN和CMAX只读Filtered监控

CMIN/CMAX MUST 使用上一发布filtered sampled-owner值执行保护和增长限制。

#### Scenario: 当前物理状态变化

- **WHEN** 当前周期物理owner变化但尚未到监控边界
- **THEN** CMIN/CMAX决策输入保持上一发布值

### Requirement: 三平面误差证据

监控 MUST 同时导出physical actual、raw MPAM、filtered MPAM及其差值。

#### Scenario: 地址交织造成抽样误差

- **WHEN** 非抽样set的owner分布与抽样set不同
- **THEN** UI和导出明确显示raw/filtered与physical之间的误差
