## ADDED Requirements

### Requirement: L3控制读取锁存监控输入

L3 CMIN/CMAX MUST 读取本地监控边界锁存的`control_sampled`输入，而不是同一边界刚计算出的
最新`filtered_sampled`发布值。

#### Scenario: filtered发布不立即控制

- **WHEN** 监控边界T基于刚关闭窗口raw owner计算出新的filtered sampled-owner
- **THEN** 该filtered sampled-owner MAY 立即用于UI、导出和证据
- **AND** CMIN/CMAX victim选择 MUST 在下一次本地监控边界前继续读取边界T之前锁存的control input

#### Scenario: 下一边界锁存

- **WHEN** 下一次本地监控边界到达
- **THEN** 上一次已发布filtered sampled-owner MUST 被锁存为新的control input
- **AND** 后续CMIN/CMAX动作才可以使用该值
