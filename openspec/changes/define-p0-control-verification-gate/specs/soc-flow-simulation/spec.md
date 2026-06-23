## ADDED Requirements

### Requirement: P0机制可信性验收

P0完成 MUST 证明控制机制可信，而不是证明任意目标必然达成。

#### Scenario: 机制生效而目标未必达

- **WHEN** 独立微测试触发CPBM、CMIN、CMAX、BMIN、BMAX、MC QoS、CBusy或CPU OSTD控制
- **THEN** 测试 MUST 验证控制动作是否按规则生效
- **AND** 不得要求目标值一定被满足

### Requirement: 授权监控状态

控制器 MUST 只读取规格授权的监控值和本地执行状态，验证用actual状态不得暗中参与控制。

#### Scenario: L3控制输入隔离

- **WHEN** CMIN或CMAX执行victim选择
- **THEN** 控制输入 MUST 来自上一发布filtered sampled owner
- **AND** physical actual occupancy只允许用于显示、导出和误差验证

#### Scenario: MC控制输入隔离

- **WHEN** BMIN、BMAX或QoS控制执行
- **THEN** 控制输入 MUST 来自上一发布filtered bandwidth和授权buffer状态
- **AND** 不得读取理想化全局目标达成状态提前调整控制

### Requirement: 非零周期控制时序

监控、决策和动作 MUST 通过明确事件或周期边界传播，不得在同一事件中读取当前真实结果并立即作为已发布监控输入。

#### Scenario: L3 filtered延迟

- **WHEN** 当前周期产生新的line owner变化
- **THEN** CMIN/CMAX在监控发布前 MUST 继续使用上一发布filtered值

#### Scenario: MC hard BMAX延迟

- **WHEN** 当前周期服务带宽超过BMAX
- **THEN** hard block MUST 在下一次监控发布后生效，而不是在同一dispatch中零周期生效

### Requirement: 最小端到端因果链

P0 MUST 至少提供两条完整可追踪因果链：L3分配控制链和MC/CPU反馈控制链。

#### Scenario: L3链

- **WHEN** L3发生miss/fill并触发CPBM、CMIN或CMAX
- **THEN** 证据 MUST 连接激励、miss/fill、victim选择、allocation/eviction/bypass、raw/filtered/actual监控和UI事件

#### Scenario: MC CPU链

- **WHEN** MC带宽、队列或CBusy触发控制
- **THEN** 证据 MUST 连接激励、MC监控、BMAX/QoS/CBusy动作、CPU OSTD变化、带宽或延迟结果和UI事件

### Requirement: 控制结果失败继续运行

目标未达、过冲、控制饱和、不可行目标、过度限流和性能恶化 MUST 作为CONTROL_OUTCOME记录，不得作为仿真失败。

#### Scenario: 目标未达

- **WHEN** 控制目标在运行结束时未达成
- **THEN** 仿真 MUST 正常完成并导出证据

#### Scenario: 控制饱和

- **WHEN** QoS、BMAX、CBusy或OSTD控制达到可配置极限仍无法达成目标
- **THEN** 仿真 MUST 继续运行并报告饱和状态

### Requirement: P0不引入专用旁路

P0验证 MUST 复用常规仿真模式、数据模型和UI通路。

#### Scenario: 验证微测试

- **WHEN** 运行P0机制微测试或控制验证套件
- **THEN** 可以使用更小的配置和确定性激励
- **AND** 不得新增阶段专用仿真模式、影子数据模型或绕过常规UI证据链的结果通路
