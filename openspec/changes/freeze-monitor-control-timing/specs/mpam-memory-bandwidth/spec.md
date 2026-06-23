## ADDED Requirements

### Requirement: MC控制读取锁存带宽输入

MC BMIN、BMAX、hard block、soft demotion和CBusy带宽项 MUST 读取本地监控边界锁存的
`control_bandwidth`输入，而不是同一边界刚计算出的最新`filtered_bandwidth`发布值。

#### Scenario: BMAX过冲后延迟断言

- **WHEN** 当前窗口服务字节使本边界发布的filtered bandwidth超过BMAX
- **THEN** 该PARTID在本边界之后的同timestamp调度 MUST NOT 因这个刚发布值立即hard block或soft demote
- **AND** hard/soft控制最早在下一次本地监控边界锁存该filtered值后生效

#### Scenario: BMAX释放延迟

- **WHEN** hard block后的窗口不再服务该PARTID并发布低于释放阈值的filtered bandwidth
- **THEN** hard block MUST 在下一次本地监控边界锁存该低filtered值后释放
- **AND** 释放延迟和过冲 MUST 记录为可观察控制结果，不得中止仿真

#### Scenario: CBusy带宽输入

- **WHEN** CBusy detector使用带宽比例判断等级
- **THEN** 带宽比例 MUST 基于`control_bandwidth / BMAX`
- **AND** queue比例仍 MAY 基于当前授权buffer状态
