## ADDED Requirements

### Requirement: MC尾部短窗口actual不参与控制效果图

控制台 MUST 保留MC snapshot的原始`interval_ns`和`achieved_bandwidth_gbps`证据，
但在控制效果和控制总览的MC带宽图中，短于当前`control_interval_ns`的尾部snapshot
MUST NOT 参与`actual`曲线绘制或纵轴autoscale。

#### Scenario: 排除final短窗口actual

- **WHEN** 仿真结束时产生`interval_ns < control_interval_ns`的MC final snapshot
- **THEN** 控制台 MUST 不绘制该snapshot的MC `actual`点
- **AND** MUST 不使用该点计算MC带宽图纵轴范围
- **AND** 表格或概览中的该点 MUST 标记为尾部窗口不参与

#### Scenario: 保留控制输入和原始证据

- **WHEN** 尾部短窗口MC actual被图表排除
- **THEN** `raw monitor`、`latest filtered BW`和`control input`曲线 MUST 继续按原始数据绘制
- **AND** 后端MSC行 MUST 继续保留`interval_ns`和原始`achieved_bandwidth_gbps`
