## MODIFIED Requirements

### Requirement: 上下文帮助

控制台 MUST 为每个可配置字段、动态表格子控件和选项提供hover与键盘focus说明。
普通配置说明必须包含含义、单位、作用位置、模型影响、边界、示例和模型状态。

#### Scenario: 检查普通配置

- **WHEN** 用户指向或focus任意非控制配置
- **THEN** 显示该字段的完整释义且不修改配置值

#### Scenario: 新增字段遗漏说明

- **WHEN** 开发者新增默认配置字段但未注册元数据
- **THEN** 自动化覆盖测试失败并指出缺失字段

### Requirement: 结构化算法说明

指向控制字段时，控制台 MUST 显示输入、保存状态、更新周期、决策规则、动作点、
恢复、交互优先级、前向进展、可观察证据和模型边界。

#### Scenario: 指向控制字段

- **WHEN** 用户指向或focus CMIN、CMAX、CPBM、BMIN、BMAX、MC QoS、CBusy、
  OSTD或闭环策略配置
- **THEN** 显示完整控制逻辑并标明当前实现与目标规格的差异

#### Scenario: 控制说明不完整

- **WHEN** 控制算法元数据缺少任一必备逻辑章节
- **THEN** 自动化完整性测试失败
