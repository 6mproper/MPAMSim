## ADDED Requirements

### Requirement: 控制总览显示control input

控制总览 MUST 将控制器实际读取的锁存值显示为control input，并与latest filtered区分。

#### Scenario: L3和MC主图

- **WHEN** 用户查看控制总览
- **THEN** 主线默认 SHOULD 显示control input
- **AND** latest filtered SHOULD 可选显示
- **AND** actual、raw和控制事件仍按显示层开关控制

#### Scenario: 文案区分

- **WHEN** UI解释filtered、control input、actual或raw
- **THEN** filtered MUST 表示最新发布滤波监控值
- **AND** control input MUST 表示控制器读取的锁存监控值
- **AND** actual MUST 标注为验证用观测值，不得描述为控制输入

### Requirement: 结果文案不以达标作为验收

UI MUST 避免把目标达成/未达成表述为自动通过/失败。

#### Scenario: 目标偏离

- **WHEN** 控制目标未达、过冲或饱和
- **THEN** UI SHOULD 显示目标偏离、需解释或控制结果
- **AND** MUST NOT 将其显示为仿真失败
