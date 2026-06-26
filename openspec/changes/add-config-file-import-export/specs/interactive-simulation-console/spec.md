## ADDED Requirements

### Requirement: 配置文件导入导出

控制台 MUST 支持把当前表单配置导出为本地JSON文件，并支持从同类JSON文件导入后恢复表单。
导出内容 MUST 使用现有`collectParameters()`等价参数集，导入恢复 MUST 使用现有表单填充路径，
不得引入第二套配置模型。

#### Scenario: 导出当前配置

- **WHEN** 用户点击导出配置
- **THEN** 控制台 MUST 生成带`schema`、`version`、`exported_at`和`parameters`字段的JSON文件
- **AND** `parameters` MUST 包含SoC、激励、resctrl-like、MPAM和策略配置

#### Scenario: 导入配置文件

- **WHEN** 用户选择有效配置JSON文件
- **THEN** 控制台 MUST 用文件中的`parameters`恢复当前表单
- **AND** MUST 刷新配置诊断、上下文说明和可视PARTID选择

#### Scenario: 拒绝无效文件

- **WHEN** 用户导入无法解析或缺少参数对象的文件
- **THEN** 控制台 MUST 保持当前表单不变
- **AND** MUST 显示错误提示
