## MODIFIED Requirements

### Requirement: 反馈控制状态

控制台 MUST 显示所选时间每个可见PARTID的控制状态。控制模式 MUST 只提供“无控制”和“有控制”两档。
“有控制”必须执行当前表单中已配置并开启的L3、MC、CPU和CBusy硬件/模型机制；控制台不得提供P99软件慢闭环
自动改写MC QoS或BMAX的控制模式。

#### Scenario: 有控制模式

- **WHEN** 用户选择“有控制”
- **THEN** 提交参数中的policy MUST 为`static_mpam`
- **AND** 所有已配置硬件机制参数 MUST 进入resolved config
- **AND** 不得生成P99软件慢闭环运行时设置更新

#### Scenario: 无控制模式

- **WHEN** 用户选择“无控制”
- **THEN** 提交参数中的policy MUST 为`no_control`
- **AND** 仿真 MUST 保留监控和配置展示，但关闭L3/MC资源强制

#### Scenario: 旧闭环配置导入

- **WHEN** 导入旧配置中的policy为`closed_loop_qos`
- **THEN** 控制台 SHOULD 将其归一为`static_mpam`
- **AND** 不得显示或执行P99慢闭环参数

### Requirement: 结构化算法说明

指向控制字段时，控制台 MUST 显示输入、保存状态、更新周期、决策规则、动作点、
恢复、交互优先级、前向进展、可观察证据和模型边界。

#### Scenario: 指向控制字段

- **WHEN** 用户指向或focus CMIN、CMAX、CPBM、BMIN、BMAX、MC QoS、CBusy或OSTD配置
- **THEN** 显示完整控制逻辑并标明当前实现与目标规格的差异
