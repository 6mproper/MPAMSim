## ADDED Requirements

### Requirement: SoC页签资源能力摘要

SoC页签 MUST 在多核、L3、NoC和Memory Controller分组末尾显示根据当前配置计算的能力摘要。

#### Scenario: 查看默认能力摘要

- **WHEN** 控制台加载默认配置
- **THEN** 多核、L3、NoC和Memory Controller分组各显示一行能力摘要
- **AND** 摘要说明该值是模型侧估算能力

#### Scenario: 修改配置后刷新摘要

- **WHEN** 用户修改SoC参数或激励参数
- **THEN** 能力摘要立即按当前表单重新计算
- **AND** 不创建新的仿真任务

### Requirement: MC时钟位于SoC页签

MC本地时钟配置 MUST 位于SoC页签的Memory Controller分组。

#### Scenario: 配置MC本地时钟

- **WHEN** 用户打开SoC页签
- **THEN** Memory Controller分组包含MC Clock MHz输入
- **AND** 策略页不再重复显示MC Clock MHz输入
