## ADDED Requirements

### Requirement: MC actual默认使用完整窗口raw值

控制台 MUST 在MC带宽图中把`actual`显示为完整统计窗口内的真实服务带宽。
actual moving average MAY 保留为独立可选趋势层，但不得替代默认`actual`。
该moving average MUST 只使用当前窗口和过去有效窗口，不得使用未来样本。

#### Scenario: 绘制MC actual raw

- **WHEN** 控制效果页或控制总览页绘制MC目标带/监控/实际图
- **THEN** `actual`曲线 MUST 使用完整统计窗口`achieved_bandwidth_gbps`
- **AND** 图例或数值标签 MUST 标明为`actual raw`或`actual`
- **AND** 原始单窗口`achieved_bandwidth_gbps` MUST 继续作为后端证据保留

#### Scenario: 可选MC actual moving average

- **WHEN** 用户打开`actual MA`显示层
- **THEN** 曲线 MUST 使用尾随4窗口moving average
- **AND** 图例或数值标签 MUST 标明为`actual MA`
- **AND** `actual MA`默认 MUST 关闭

#### Scenario: 不改变控制输入

- **WHEN** MC actual moving average被显示
- **THEN** BMIN、BMAX、CBusy和QoS控制 MUST 继续只读取授权的monitor/control input
- **AND** MUST NOT 读取actual raw或actual moving average作为控制输入
