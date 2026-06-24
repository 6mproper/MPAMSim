## ADDED Requirements

### Requirement: 图表轴单位可见

Web控制台 MUST 在所有结果图表上显示横轴和纵轴的单位或类别语义。

#### Scenario: 时间序列图

- **WHEN** 控制台绘制P99、带宽、队列、L3控制效果、MC控制效果、QoS或P99目标时间序列
- **THEN** 横轴 MUST 标明时间单位
- **AND** 纵轴 MUST 标明对应指标单位

#### Scenario: 延迟分解柱状图

- **WHEN** 控制台绘制延迟分解柱状图
- **THEN** 横轴 MUST 标明类别语义
- **AND** 纵轴 MUST 标明延迟单位
