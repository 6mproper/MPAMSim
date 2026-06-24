## ADDED Requirements

### Requirement: resctrl-like软件组配置页

Web控制台 MUST 提供可选resctrl-like页签，让用户通过CTRL_MON group、MON group、`schemata`、`tasks`和`cpus_list`配置软件资源组，同时保留原始线程模式和原始MPAM配置页。

#### Scenario: 默认不改变原始模式

- **WHEN** 控制台加载默认配置
- **THEN** resctrl-like模式 MUST 默认为关闭
- **AND** 16线程激励仍直接使用原始PARTID/PMG配置

#### Scenario: 启用软件资源组

- **WHEN** 用户启用resctrl-like模式并提交仿真
- **THEN** 控制台 MUST 在提交前把软件组映射为现有16线程PARTID/PMG配置和16组PARTID控制
- **AND** MUST NOT 新增独立仿真运行模式或专用结果通路

### Requirement: resctrl-like软件接口可见

resctrl-like页签 MUST 显示软件可见的mount/options、info、控制组树、内部PARTID/PMG映射、`last_cmd_status`诊断和`mon_data`风格监控读数。

#### Scenario: 软件组映射可解释

- **WHEN** 用户修改`tasks`、`cpus_list`或MON group
- **THEN** UI SHOULD 显示每个组映射的内部PARTID/PMG
- **AND** SHOULD 显示任务优先于CPU默认组、否则落到root组的说明

#### Scenario: 监控读数复用现有结果

- **WHEN** 已有仿真结果且resctrl-like模式启用
- **THEN** `mon_data`视图 MUST 从现有L3/MC监控结果读取`llc_occupancy`、`mbm_total_bytes`和`mbm_local_bytes`风格读数
- **AND** MUST NOT 直接读取控制器私有actual状态作为软件监控输入
