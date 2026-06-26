## MODIFIED Requirements

### Requirement: 3-bit QoS仲裁

当前MC scheduler MUST 先计算raw 3-bit effective QoS：
`raw_effective_qos = clamp(base_qos + bmin_promote - softlimit_demote + service_deficit, 0, 7)`。
MC MUST 支持可配置的8级到4级映射开关。关闭时，最终仲裁QoS MUST 等于raw 3-bit effective QoS。
开启时，最终仲裁QoS MUST 按`0,1,2,3,4,5,6,7 -> 0,1,1,1,2,2,2,3`映射。
MC MUST 使用最终仲裁QoS选择最高档，相同最终QoS使用rotating buffer-slot scan。

#### Scenario: 映射关闭

- **GIVEN** MC QoS映射开关关闭
- **AND** ready entry A的raw effective QoS为1，ready entry B的raw effective QoS为2
- **WHEN** MC执行候选选择
- **THEN** B MUST 因最终QoS更高而优先于A

#### Scenario: 映射开启

- **GIVEN** MC QoS映射开关开启
- **AND** ready entry A的raw effective QoS为1，ready entry B的raw effective QoS为2
- **WHEN** MC执行候选选择
- **THEN** A和B最终仲裁QoS都为1
- **AND** MC MUST 使用rotating buffer-slot scan在同档候选中选择

#### Scenario: QoS证据

- **WHEN** MC导出监控快照
- **THEN** 每个PARTID和监控组 MUST 提供raw effective QoS统计、最终effective QoS统计、映射开关状态和映射事件计数
