## ADDED Requirements

### Requirement: MC监控和控制输入使用阶梯线

控制台 MUST 将MC带宽图中的离散监控/控制状态绘制为阶梯线，而不是普通插值折线。

#### Scenario: 控制效果MC带宽图

- **WHEN** 控制效果页绘制MC目标带/监控/实际图
- **THEN** `raw monitor`、`latest filtered BW`和`control input` MUST 使用阶梯线
- **AND** `actual` MUST NOT 使用阶梯线

#### Scenario: 控制总览MC带宽图

- **WHEN** 控制总览页绘制MC目标带/监控/实际图
- **THEN** `raw monitor`、`latest filtered BW`和`control input` MUST 使用阶梯线
- **AND** 不得改变MC监控、滤波或控制算法
