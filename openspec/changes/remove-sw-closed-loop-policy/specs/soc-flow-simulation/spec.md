## MODIFIED Requirements

### Requirement: 控制上下文扩展边界

后续新增控制能力 MUST 通过类型化`ControlContext`读取授权监控样本、资源scope、
上一控制状态和动作生效边界；P1不因此扩展到完整SoC仿真。当前平台不提供P99软件慢闭环策略作为硬件验证路径；
`target_p99_ns`只作为结果目标线或KPI参考，不得自动改写MPAM设置表。

#### Scenario: 新控制策略

- **WHEN** 新增NoC QoS、PE侧限流、多MC协同或PMG策略
- **THEN** SHOULD 通过`ControlContext`声明授权输入
- **AND** MUST NOT 直接读取私有actual状态或阶段专用数据面
- **AND** MUST NOT 以端到端P99软件策略替代硬件可见监控和控制机制
