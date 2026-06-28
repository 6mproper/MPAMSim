## ADDED Requirements

### Requirement: MC actual使用尾随moving average

控制台 MUST 在MC带宽图中把`actual`显示为尾随moving average，而不是单窗口完成带宽。
该moving average MUST 只使用当前窗口和过去有效窗口，不得使用未来样本。

#### Scenario: 绘制MC actual moving average

- **WHEN** 控制效果页或控制总览页绘制MC目标带/监控/实际图
- **THEN** `actual`曲线 MUST 使用尾随4窗口moving average
- **AND** 图例或数值标签 MUST 标明为`actual MA`
- **AND** 原始单窗口`achieved_bandwidth_gbps` MUST 继续作为后端证据保留

#### Scenario: 不改变控制输入

- **WHEN** MC actual moving average被显示
- **THEN** BMIN、BMAX、CBusy和QoS控制 MUST 继续只读取授权的monitor/control input
- **AND** MUST NOT 读取actual moving average或原始actual作为控制输入
