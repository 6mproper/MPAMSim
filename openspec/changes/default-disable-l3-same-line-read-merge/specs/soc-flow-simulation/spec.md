## MODIFIED Requirements

### Requirement: L3 MSHR和同Line合并

L3 MUST 支持可配置的同一cache line并发read miss合并；默认配置 MUST 关闭合并，以保留
每笔miss对MSHR、MC和流控路径的独立压力。

#### Scenario: 默认关闭合并

- **WHEN** `merge_same_line_misses`未显式开启，且PARTID 0先miss、PARTID 1在fill前read同一line
- **THEN** 两个read miss MUST 保持独立MSHR/MC请求路径
- **AND** 后返回fill发现line已存在时 MUST 记录redundant fetch证据且不改写line owner

#### Scenario: 显式开启合并

- **WHEN** `merge_same_line_misses`显式开启，且PARTID 0先miss、PARTID 1在fill前read同一line
- **THEN** 只发一个MC请求，fill owner为PARTID 0，两个请求分别返回完成
