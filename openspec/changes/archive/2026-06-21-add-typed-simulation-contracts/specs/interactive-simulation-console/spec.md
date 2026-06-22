## MODIFIED Requirements

### Requirement: MPAM结果可视化

控制台 MUST 只消费collector发布的类型化监控和控制事件投影，不直接读取NoC、L3、
MC或requester私有字段。

#### Scenario: 现有Web任务运行

- **WHEN** 类型化契约接入当前数据通路
- **THEN** 现有周期表格、控制记录和最终报告保持可用
