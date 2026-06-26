## MODIFIED Requirements

### Requirement: CBusy配置和证据

控制台 MUST 配置CBusy阈值、时序、CPU响应开关、L3响应开关、L3 QoS调度开关、
L3 CBusy QoS降档步长和OSTD cap，并显示MC detector、CPU有效OSTD和L3响应证据。

#### Scenario: 观察CBusy

- **WHEN** MC提升某PARTID CBusy
- **THEN** MC视图显示detector，CPU视图显示有效OSTD和stall
- **AND** L3视图 SHOULD 显示CBusy level、MSHR cap、QoS demote、effective QoS和MSHR block证据

#### Scenario: 关闭响应动作

- **WHEN** 用户关闭CPU或L3 CBusy响应开关
- **THEN** 对应资源 MUST 仍可显示收到/生成的CBusy证据
- **AND** 对应资源 MUST NOT 执行该层的限流动作

### Requirement: 流控算法配置

当前控制台 MUST 配置L3 queue/parallelism、L3 QoS调度、L3 CBusy QoS降档和MC token、aging、BMIN提升及soft penalty。

#### Scenario: 修改L3 QoS调度参数

- **WHEN** 用户修改L3 QoS调度开关或CBusy降档步长
- **THEN** submitted config和L3监控快照 MUST 使用新值
