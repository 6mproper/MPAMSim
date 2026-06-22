## ADDED Requirements

### Requirement: 可配MC地址交织

仿真 MUST 支持linear和XOR地址交织，并在CPU发射前确定目标MC。

#### Scenario: 相同配置复现

- **WHEN** 两次仿真使用相同地址、granularity、XOR shift和MC数量
- **THEN** 每个地址映射到相同MC
