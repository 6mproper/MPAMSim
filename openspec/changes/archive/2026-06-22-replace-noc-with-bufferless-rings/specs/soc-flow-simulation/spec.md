## ADDED Requirements

### Requirement: 三条双向Bufferless Ring

系统 MUST 使用独立REQ、RSP和DAT双向bufferless ring。Ring内部flit MUST 每个hop周期
前进，且MUST NOT按PARTID或QoS仲裁。

#### Scenario: 最短方向

- **WHEN** source到destination的两个方向距离不同
- **THEN** flit选择hop数更少的方向

#### Scenario: 等距方向

- **WHEN** 两个方向距离相同
- **THEN** 使用配置的固定tie方向且重复运行结果一致

### Requirement: 目的端拒绝后绕行

flit到达目标节点但endpoint不能接收时 MUST 继续移动并在下一周再次尝试下Ring。

#### Scenario: MC Buffer暂满

- **WHEN** REQ flit到达MC而MC不能接收
- **THEN** flit不丢失、不停止且记录failed ejection和完整绕环

### Requirement: REQ注入参与CPU准入

CPU MUST 在分配transaction ID和OSTD前确认REQ Ring源link有可用槽。

#### Scenario: REQ Ring满

- **WHEN** Thread、Core和CBusy允许但REQ源link没有空槽
- **THEN** 待发描述保留在源端并记录`req_ring` stall，不增加OSTD

### Requirement: DAT逐Flit传输

DAT MUST 按配置flit大小拆分、独立注入和移动，并在全部flit下Ring后完成transaction。

#### Scenario: 64B DAT使用16B flit

- **WHEN** 一个64B read data返回
- **THEN** 生成4个DAT flit且只在4个flit全部下Ring后释放CPU OSTD
