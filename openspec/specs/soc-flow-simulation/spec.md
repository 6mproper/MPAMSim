# soc-flow-simulation 规格

## Purpose

定义当前已实现的确定性系统级仿真路径、配置边界、延迟归因、CPU OSTD监控、
控制机制比较和可复现输出契约，作为当前代码行为的机器可验证能力基线。

## Requirements

### Requirement: 确定性系统级仿真

配置和随机种子不变时，系统 MUST 确定性地执行离散事件SoC模型。

#### Scenario: 重复相同运行

- **WHEN** 两次仿真使用相同的已校验配置和seed
- **THEN** issued、completed和报告指标 MUST 一致

### Requirement: 可配置多核请求路径

系统 MUST 以因果请求路径建模可配置core、thread、requester、NoC、共享L3/SLC和MC。

#### Scenario: 增加活动requester

- **WHEN** workload使用`per_requester`注入且活动requester增加
- **THEN** offered traffic和共享资源竞争增加，且无需修改源码

### Requirement: 流控延迟归因

系统 MUST 把完成请求延迟分解为NoC、cache、memory queue、memory service和throttle。

#### Scenario: 诊断带宽限制

- **WHEN** hard BMAX延迟请求
- **THEN** 导出指标 MUST 把throttle delay与queue/service delay分开

### Requirement: 可复现输出

系统 MUST 导出resolved config、topology、run summary、每PARTID指标、每MSC指标、
timeline和control trace。

#### Scenario: 完成仿真

- **WHEN** 仿真正常完成且启用输出
- **THEN** MUST 生成JSON、CSV和可选静态HTML报告

### Requirement: 独立硬件线程workload

Web配置构建器 MUST 为16线程矩阵中每个启用行生成一个workload，并绑定固定requester。

#### Scenario: 启用全部激励

- **WHEN** 16行全部启用
- **THEN** resolved config包含16个workload并绑定16个不同CPU线程requester

#### Scenario: 关闭一个激励

- **WHEN** 一个激励行被关闭
- **THEN** 不为该requester生成workload，其他映射保持不变

### Requirement: 激励配置校验

每个启用激励 MUST 只生成一个注入速率字段，并校验PARTID、PMG、size、read ratio、
working set和target。

#### Scenario: 使用MRPS

- **WHEN** 激励选择MRPS
- **THEN** 只生成`injection_rate_mrps`

#### Scenario: 使用Gbps

- **WHEN** 激励选择Gbps
- **THEN** 只生成`injection_rate_gbps`

### Requirement: Web任务安全上限

构建器 MUST 估算全部启用激励的请求总量，并拒绝超过Web任务上限的配置。

#### Scenario: 总流量过大

- **WHEN** 估算请求数超过2,000,000
- **THEN** MUST 在启动仿真前拒绝任务

### Requirement: 每PARTID CPU OSTD监控

仿真器 MUST 在每个控制周期采样requester的PARTID OSTD，且不引入CPU流水线模型。

#### Scenario: 采样OSTD

- **WHEN** 捕获控制周期
- **THEN** 每个requester/PARTID报告当前值、周期峰值、配置上限、issued/completed和backpressure

#### Scenario: 重置周期峰值

- **WHEN** 一个CPU监控周期结束
- **THEN** 下一周期峰值从当前OSTD开始

### Requirement: CBusy控制有效OSTD

requester MUST 把延迟到达的每PARTID CBusy作为有效OSTD上限，同时保留原配置上限。

#### Scenario: 多MC反馈

- **WHEN** 多个MC对同一PARTID反馈CBusy
- **THEN** 当前实现使用最高等级及对应上限

#### Scenario: CBusy源端阻塞

- **WHEN** PARTID达到CBusy上限但未达到requester总上限
- **THEN** 新请求重试，延迟归因到CBusy stall

#### Scenario: 保证基本前向进展

- **WHEN** Level 3 CBusy生效
- **THEN** 有效OSTD至少为1，已发请求可以完成

### Requirement: 可复现机制比较

仿真器 MUST 能够派生只改变控制开关、保持workload、topology、duration和seed不变的案例。

#### Scenario: 派生比较案例

- **WHEN** 提交有效配置
- **THEN** 四个派生案例保持非控制输入不变并使用static policy

### Requirement: 确定性机制微测试

仿真器 MUST 支持隔离cache最小/最大和memory bandwidth最小/最大行为的内置workload。

#### Scenario: 重复验证套件

- **WHEN** 两次使用相同参数和seed
- **THEN** 检查结果和证据一致

### Requirement: 目标与效果证据

仿真器 MUST 输出足够的周期证据，用于比较cache、bandwidth、QoS和latency目标与结果。

#### Scenario: 分析完整运行

- **WHEN** 仿真完成
- **THEN** 用户可以直接根据周期快照计算目标符合度
