## MODIFIED Requirements

### Requirement: 独立硬件线程workload

Web配置构建器 MUST 为`active_cores × threads_per_core`矩阵中每个启用行生成一个workload，
并绑定由slot和每核线程数计算出的固定requester。

#### Scenario: 启用全部激励

- **WHEN** 4C2T拓扑的8行全部启用
- **THEN** resolved config包含8个workload并绑定8个不同CPU线程requester

#### Scenario: 扩展16C2T拓扑

- **WHEN** 16C2T拓扑使用默认激励
- **THEN** resolved config包含32个workload并绑定32个不同CPU线程requester

#### Scenario: 关闭一个激励

- **WHEN** 一个激励行被关闭
- **THEN** 不为该requester生成workload，其他映射保持不变
