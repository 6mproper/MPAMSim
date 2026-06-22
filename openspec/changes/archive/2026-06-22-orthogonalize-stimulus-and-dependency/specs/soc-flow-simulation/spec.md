## ADDED Requirements

### Requirement: 独立依赖模式配置

workload MUST 支持dependency_mode字段（independent/pointer_chain）。pointer_chain模式下每条链同时最多一个未完成请求，必须等待前一事务返回后才能生成下一地址。

#### Scenario: pointer_chain串行化

- **WHEN** dependency_mode=pointer_chain
- **THEN** 同一链上的请求严格串行，前一请求未返回时不生成新地址
