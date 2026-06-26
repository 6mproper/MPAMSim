## MODIFIED Requirements

### Requirement: L3本地周期MPAM监控

L3 MUST 每个可配本地监控周期发布所有PARTID的raw sampled-owner、published sampled-owner、
control sampled-owner和抽样访问带宽。L3 occupancy是缓存状态的抽样绝对值，
不得把CMIN/CMAX输入建模成带宽式递归滤波值。

#### Scenario: 256拍发布

- **WHEN** L3运行到一个监控周期边界
- **THEN** raw sampled-owner MUST 读取当前采样offset对应的sampled-owner counter bank
- **AND** published sampled-owner MUST 作为该边界对外发布的sampled-owner快照
- **AND** control sampled-owner MUST 锁存为后续控制窗口读取的control input
- **AND** sampled access bandwidth MAY 按`history_weight + current_weight = 1`的权重滤波
