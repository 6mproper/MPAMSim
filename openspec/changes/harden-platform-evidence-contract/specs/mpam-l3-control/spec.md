## ADDED Requirements

### Requirement: L3控制事件证据

L3 CMIN/CMAX内部控制状态切换 MUST 复用常规`ControlEvent`通路。

#### Scenario: CMIN CMAX状态变化

- **WHEN** L3本地监控边界锁存的control input改变CMIN保护或CMAX限制状态
- **THEN** MUST 导出`limit_state_changed`控制事件
- **AND** 事件 MUST 引用`control_input` monitor sample
- **AND** 事件 SHOULD 包含control sampled-owner、quota和latest filtered证据
