## ADDED Requirements

### Requirement: L3控制读取已发布抽样占用输入

L3 CMIN/CMAX MUST 读取本地监控边界发布并保存的`control_sampled`输入，而不是窗口内尚未发布的
即时physical或raw owner状态。

#### Scenario: 窗口内物理变化不立即控制

- **WHEN** 当前控制窗口内发生新的line owner变化但还未到L3监控边界
- **THEN** CMIN/CMAX victim选择 MUST 继续读取已保存的control input

#### Scenario: 边界后新窗口使用

- **WHEN** L3监控边界T发布新的sampled-owner占用
- **THEN** 该值 MUST 被保存为后续控制窗口的control input
- **AND** 边界T之前已经完成的victim选择不得回溯使用该值
