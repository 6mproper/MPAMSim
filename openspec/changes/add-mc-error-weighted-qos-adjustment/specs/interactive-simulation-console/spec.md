## MODIFIED Requirements

### Requirement: 直接配置

控制台 MUST 允许用户配置SoC、由SoC拓扑展开的硬件线程激励、仿真时序、policy和16组PARTID控制，
无需修改源码。控制台 MUST 支持在MC调度算法参数中选择QoS调整模式：
`fixed_step`或`error_weighted`。

#### Scenario: 配置MC QoS调整模式

- **WHEN** 用户选择`fixed_step`
- **THEN** 控制台 MUST 提交固定BMIN升档和softlimit降档参数
- **WHEN** 用户选择`error_weighted`
- **THEN** 控制台 MUST 提交BMIN/BMAX error weight、deadband、max delta和quantization参数

### Requirement: 上下文帮助

控制台 MUST 对关键配置项、结果图例和控制算法提供点击打开的中文释义。

#### Scenario: 查看MC error-weighted参数说明

- **WHEN** 用户点击MC QoS调整模式、deadband、max delta或quantization说明
- **THEN** 控制台 MUST 说明该参数如何影响基于control bandwidth误差的QoS delta
- **AND** MUST 标明控制器不得读取actual/debug带宽
