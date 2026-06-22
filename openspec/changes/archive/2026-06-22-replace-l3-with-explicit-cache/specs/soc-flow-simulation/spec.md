## ADDED Requirements

### Requirement: 真实L3 Tag和替换

L3 MUST 使用真实set/tag/way状态决定hit/miss，并支持确定性LRU和PLRU。

#### Scenario: 重复访问已fill地址

- **WHEN** 一个地址miss、完成fill后再次访问且未被驱逐
- **THEN** 第二次访问命中同一tag且不访问MC

### Requirement: L3 MSHR和同Line合并

默认配置下，同一cache line的并发read miss MUST 合并为一个MC请求，并保留每个waiter的
独立CPU OSTD。

#### Scenario: 两个PARTID访问同一未缓存Line

- **WHEN** P0先miss且P1在fill前read同一line
- **THEN** 只发一个MC请求，fill owner为P0，两个请求分别返回完成

### Requirement: Fill Buffer和返回完成

MC DAT MUST 在L3 fill buffer可接收时下Ring，完成fill后才向CPU返回并释放OSTD。

#### Scenario: Fill Buffer满

- **WHEN** DAT到达L3且fill buffer没有空entry
- **THEN** DAT继续在Ring绕行且不提前完成MSHR waiter
