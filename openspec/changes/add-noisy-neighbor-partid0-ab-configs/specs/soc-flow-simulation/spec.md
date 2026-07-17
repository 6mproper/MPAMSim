## ADDED Requirements

### Requirement: 高OSTD noisy-neighbor单变量A/B配置

仓库 MUST 提供两份Web UI可导入JSON配置，使用PARTID 0高OSTD噪声流和PARTID 1低OSTD受保护流竞争同一MC。两份配置 MUST 仅以CPU是否执行CBusy反馈区分控制路径。

#### Scenario: JSON恢复每requester OSTD

- **WHEN** 用户导入任一对比配置
- **THEN** 激励表 MUST 显示cpu0.t0基础OSTD为32、cpu1.t0基础OSTD为4
- **AND** Web构建器 MUST 生成对应的两个显式CPU requester
- **AND** 旧JSON缺少每requester OSTD时 MUST 继承SoC默认Thread OSTD

#### Scenario: 受保护流的BMIN可行性

- **WHEN** PARTID 1以相同激励和基础OSTD单独运行
- **THEN** 其实际带宽 MUST 能达到配置BMIN

#### Scenario: CPU不响应CBusy

- **WHEN** 两个PARTID共同运行且CPU不执行CBusy cap
- **THEN** MC MUST 仍能产生PARTID 0的CBusy检测证据
- **AND** PARTID 0 effective OSTD MUST 保持基础配置值
- **AND** PARTID 1 MAY 因竞争而低于BMIN

#### Scenario: CPU响应CBusy

- **WHEN** 两个PARTID共同运行且CPU执行CBusy cap
- **THEN** PARTID 0 effective OSTD MUST 降低
- **AND** PARTID 0 MUST 产生CBusy准入stall
- **AND** PARTID 1实际带宽 SHOULD 相对开环提高

#### Scenario: 排除混杂控制

- **WHEN** 比较两份配置
- **THEN** BMIN QoS提升、Soft BMAX QoS降档、aging、L3 QoS和L3 CBusy响应 MUST 保持关闭
- **AND** request QoS和MPAM config QoS MUST 在两个PARTID之间相同
