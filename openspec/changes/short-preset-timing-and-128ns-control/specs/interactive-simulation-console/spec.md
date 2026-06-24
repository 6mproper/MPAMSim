## MODIFIED Requirements

### Requirement: 直接配置

控制台 MUST 允许用户配置SoC、16线程激励、仿真时序、policy和16组PARTID控制，
无需修改源码。

#### Scenario: 配置非默认PARTID

- **WHEN** 用户修改任意PARTID控制
- **THEN** 提交任务使用统一校验schema中的设置

#### Scenario: 默认短窗口仿真

- **WHEN** 控制台加载默认配置
- **THEN** 默认仿真时间 MUST 为`5000ns`
- **AND** 默认控制周期 MUST 为`128ns`
- **AND** 控制周期输入 MUST 允许最小`128ns`

### Requirement: 控制效果预设

控制台 MUST 提供多组服务端定义的预设配置，用于触发可见MSC监控和控制效果。

#### Scenario: 查看预设列表

- **WHEN** 控制台加载默认配置
- **THEN** payload包含至少三组预设
- **AND** 每组预设包含id、名称、说明、预期观察点和完整参数
- **AND** 每组预设的仿真时间 MUST 为`5000ns`
- **AND** 每组预设的控制周期 MUST 为`128ns`
