## MODIFIED Requirements

### Requirement: 配置帮助契约

控制台 MUST 为每个可配置字段、动态表格子控件和选项提供点击打开的说明。
普通配置说明必须包含含义、单位、作用位置、模型影响、边界、示例和模型状态。
悬停、移出、focus和blur MUST NOT 打开或关闭说明。

#### Scenario: 查看普通字段说明

- **WHEN** 用户点击任意非控制配置
- **THEN** 显示该字段的完整释义且不修改配置值

#### Scenario: 关闭普通字段说明

- **WHEN** 普通字段说明已经打开
- **AND** 用户再次点击同一目标、点击空白处或按ESC
- **THEN** 说明关闭

### Requirement: 结构化算法说明

点击控制字段时，控制台 MUST 显示输入、保存状态、更新周期、决策规则、动作点、
恢复、交互优先级、前向进展、可观察证据和模型边界。悬停、移出、focus和blur
MUST NOT 打开或关闭算法说明。

#### Scenario: 查看控制字段说明

- **WHEN** 用户点击CMIN、CMAX、CPBM、BMIN、BMAX、MC QoS、CBusy或OSTD配置
- **THEN** 显示完整控制逻辑并标明当前实现与目标规格的差异

#### Scenario: 关闭控制字段说明

- **WHEN** 算法说明已经打开
- **AND** 用户再次点击同一目标、点击空白处、点击关闭按钮或按ESC
- **THEN** 算法说明关闭

### Requirement: 控制总览解释提示紧凑化

控制总览 MUST 使用紧凑说明提示解释曲线显示层和算法规则。

#### Scenario: 查看曲线层解释

- **WHEN** 用户点击目标带、filtered、actual、raw或控制事件选项
- **THEN** 控制台显示该显示层的独立解释

#### Scenario: 查看算法解释

- **WHEN** 用户点击控制总览中的算法说明目标
- **THEN** 算法说明以紧凑键值文本展示
- **AND** 不使用大面积分区卡片遮挡图表
