## ADDED Requirements

### Requirement: MC控制事件证据

MC BMIN/BMAX内部控制状态切换 MUST 复用常规`ControlEvent`通路。

#### Scenario: BMIN BMAX状态变化

- **WHEN** MC本地监控边界锁存的control bandwidth改变UNDER_BMIN、OVER_BMAX或hard block状态
- **THEN** MUST 导出`limit_state_changed`控制事件
- **AND** 事件 MUST 引用`control_input` monitor sample
- **AND** 事件 SHOULD 包含control bandwidth、latest filtered、阈值、滞回和limit mode证据
