## ADDED Requirements

### Requirement: resctrl-like软件组转换

Web配置构建器 MUST 支持可选resctrl-like软件组输入，并在仿真配置生成阶段转换为现有硬件线程workload标签和MPAM MSC settings table。

#### Scenario: CTRL_MON group映射PARTID

- **WHEN** resctrl-like模式启用且CTRL_MON group有效
- **THEN** 每个CTRL_MON group MUST 映射到一个唯一内部PARTID
- **AND** group的L3/MB `schemata` MUST 转换为对应PARTID的CPBM和MC BMAX设置

#### Scenario: MON group映射PMG

- **WHEN** 某任务或CPU被放入CTRL_MON group下的MON group
- **THEN** 新事务 MUST 使用该CTRL_MON group的PARTID和该MON group的PMG
- **AND** PMG作用域 MUST 限定在同一个PARTID内

#### Scenario: 任务优先于CPU默认组

- **WHEN** 一个硬件线程同时被任务列表和CPU列表覆盖
- **THEN** 显式`tasks`归属 MUST 优先于`cpus_list`
- **AND** 未命中的线程 MUST 使用root group

#### Scenario: 不新增控制器输入

- **WHEN** resctrl-like模式转换完成后运行仿真
- **THEN** 控制器 MUST 仍然只读取现有授权MPAM监控值、本地执行状态和配置状态
- **AND** MUST NOT 读取resctrl UI的验证用actual数据作为控制输入
