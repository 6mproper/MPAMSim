## ADDED Requirements

### Requirement: 类型化跨模块事务

仿真器 MUST 使用单一`Transaction`类型在requester、NoC、L3和MC之间传递请求，
并显式保存路由、延迟、完成条件和仲裁结果，禁止组件写入未声明动态属性。

#### Scenario: MC完成一次仲裁

- **WHEN** MC选择一个候选请求
- **THEN** base QoS、effective QoS、aging、BMIN和soft BMAX结果写入声明的仲裁状态

#### Scenario: 保留旧导入路径

- **WHEN** 现有代码从`src.traffic.request`导入`Request`
- **THEN** 得到与`Transaction`相同的权威运行时类型

### Requirement: 类型化监控和控制因果链

每个MSC MUST 发布类型化监控快照和样本，控制动作 MUST 通过稳定ID连接监控样本、
决策、动作生效时间及后续导出记录。

#### Scenario: 慢速策略更新设置

- **WHEN** policy根据一个控制周期的指标修改MPAM设置
- **THEN** control event保存monitor sample ID、decision ID、old/new state和生效时间

### Requirement: 组件能力声明

每个可运行组件 MUST 声明输入输出、能力、所需监控、动作、验证钩子、近似和不兼容组合。

#### Scenario: 注册当前组件

- **WHEN** Simulation完成NoC、L3和MC构建
- **THEN** registry校验唯一ID并导出全部组件能力
