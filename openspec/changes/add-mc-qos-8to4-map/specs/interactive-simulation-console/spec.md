## MODIFIED Requirements

### Requirement: 流控算法配置

当前控制台 MUST 配置L3 queue/parallelism、L3 QoS调度、L3 CBusy QoS降档和MC token、aging、BMIN提升及soft penalty。
控制台 MUST 配置MC QoS 8级到4级映射开关。该开关关闭时MC按8级final QoS仲裁；
开启时MC按`01234567 -> 01112223`映射后的4级final QoS仲裁。

#### Scenario: 修改MC QoS映射

- **WHEN** 用户修改MC QoS 8级到4级映射开关
- **THEN** submitted config和MC监控快照 MUST 使用新值
- **AND** MC资源监控 SHOULD 显示raw effective QoS和实际final effective QoS
