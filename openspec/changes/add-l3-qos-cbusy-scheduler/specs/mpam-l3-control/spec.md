## ADDED Requirements

### Requirement: L3 QoS调度

L3 MUST 支持可配置的本地QoS调度。开启时，L3 lookup入口队列和MSHR等待队列
MUST 在本地full-depth候选中选择effective QoS最高的请求；同档请求 MUST 保持FIFO顺序。

#### Scenario: Lookup入口选择

- **WHEN** L3 lookup入口队列同时存在多个等待请求且QoS调度开启
- **THEN** L3 MUST 选择effective QoS最高的请求进入lookup槽
- **AND** effective QoS相同的请求 MUST 保持原FIFO顺序

#### Scenario: MSHR等待选择

- **WHEN** L3 MSHR等待队列中存在多个请求且至少一个请求可准入
- **THEN** L3 MUST 在可准入请求中选择effective QoS最高的请求分配MSHR
- **AND** 因CBusy MSHR cap暂不可准入的请求 MUST 保留等待，不得阻塞其他可准入请求

#### Scenario: 关闭QoS调度

- **WHEN** L3 QoS调度开关关闭
- **THEN** lookup入口队列和MSHR等待队列 MUST 保持FIFO行为

### Requirement: MC CBusy驱动L3 QoS降档

L3 effective QoS MUST 使用PARTID base QoS和L3已学习的CBusy level计算。

```text
base_qos = PARTID 3-bit QoS if enabled else 0
demote = cbusy_level * l3_cbusy_qos_demote_per_level
effective_qos = clamp(base_qos - demote, 0, 7)
```

#### Scenario: CBusy降档

- **WHEN** L3从返回路径学习到PARTID P的CBusy level大于0
- **THEN** P后续L3 QoS调度 MUST 使用降档后的effective QoS
- **AND** 目标MC ID MUST 只作为反馈来源证据，不作为L3 QoS调度索引

#### Scenario: 前向进展

- **WHEN** 某PARTID effective QoS降到0
- **THEN** L3仍 MUST 在没有更高QoS可准入请求时服务该PARTID
- **AND** hit、fill、response和已分配MSHR MUST NOT 被QoS调度撤销
