## MODIFIED Requirements

### Requirement: CBusy返回旁带

MC MUST 每`cbusy_sample_ns`更新每PARTID CBusy level，但L3/RN只能从自己收到的终端RSP或最后DAT
旁带学习对应返回事务的PARTID状态。MC ID只作为反馈来源证据，不作为CPU/L3响应动作索引。

#### Scenario: 返回携带CBusy

- **WHEN** MC服务完成一个请求
- **THEN** transaction MUST 采样当前MC对该PARTID的CBusy level和OSTD cap并随返回路径携带

#### Scenario: 仅更新返回路径上的观察者

- **WHEN** 返回到达L3或requester R
- **THEN** 只有该返回路径上的L3/R更新对应PARTID反馈状态，同PARTID其他requester MUST 不被广播更新

#### Scenario: 无返回保持陈旧

- **WHEN** MC本地CBusy level变化但某L3/RN没有收到对应PARTID返回
- **THEN** 该L3/RN继续使用旧反馈状态
