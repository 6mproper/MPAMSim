## ADDED Requirements

### Requirement: 控制效果预设

控制台 MUST 提供多组服务端定义的预设配置，用于触发可见MSC监控和控制效果。

#### Scenario: 查看预设列表

- **WHEN** 控制台加载默认配置
- **THEN** payload包含至少三组预设
- **AND** 每组预设包含id、名称、说明、预期观察点和完整参数

### Requirement: 应用预设不自动运行

用户应用预设时，控制台 MUST 更新当前表单参数，但不得自动启动仿真。

#### Scenario: 应用MC控制预设

- **WHEN** 用户选择并应用MC BMAX/CBusy预设
- **THEN** SoC参数、16线程激励、16 PARTID控制表和策略字段更新
- **AND** 仿真状态仍保持ready或当前状态，不创建新的运行任务

### Requirement: 预设可构建

每组预设 MUST 通过现有配置构建和校验路径。

#### Scenario: 构建所有预设

- **WHEN** 测试遍历所有预设参数
- **THEN** `build_config`不报错，并保留16行激励和16组PARTID配置
