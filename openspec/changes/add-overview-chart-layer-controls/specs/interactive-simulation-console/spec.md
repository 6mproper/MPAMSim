## ADDED Requirements

### Requirement: 控制总览曲线显示层可配置

控制台 MUST 允许用户在控制总览中选择 L3/MC 曲线显示层。

#### Scenario: 切换曲线显示层

- **WHEN** 用户在控制总览中勾选或取消勾选目标带、filtered、actual、raw或控制事件
- **THEN** L3和MC图表立即按所选显示层重绘
- **AND** 不创建新的仿真任务

#### Scenario: 默认显示层

- **WHEN** 控制台首次加载
- **THEN** 目标带、filtered、actual和控制事件默认开启
- **AND** raw采样默认关闭

#### Scenario: 图例跟随显示层

- **WHEN** 用户关闭某个显示层
- **THEN** 该显示层的曲线或标记不再绘制
- **AND** 图例中不再显示该显示层

### Requirement: 控制总览解释提示紧凑化

控制总览 MUST 使用紧凑说明提示解释曲线显示层和算法规则。

#### Scenario: 查看曲线层解释

- **WHEN** 用户点击目标带、filtered、actual、raw或控制事件选项
- **THEN** 控制台显示该显示层的独立解释

#### Scenario: 查看算法解释

- **WHEN** 用户点击控制总览中的算法说明目标
- **THEN** 算法说明以紧凑键值文本展示
- **AND** 不使用大面积分区卡片遮挡图表
