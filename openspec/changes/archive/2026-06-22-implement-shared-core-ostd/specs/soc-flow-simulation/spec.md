## ADDED Requirements

### Requirement: 两级CPU OSTD

每个硬件线程 MUST 维护独立thread OSTD，属于同一core的两个线程 MUST 共享core OSTD池。

#### Scenario: 两线程竞争共享池

- **WHEN** 两个SMT线程的thread OSTD之和达到core limit
- **THEN** 后续新事务留在源端，任一事务完成后可继续准入

### Requirement: 可配置Core OSTD策略

Core OSTD池 MUST 支持shared、static_partition和reserve_borrow，并在eligible pending线程间
使用确定性work-conserving round-robin。

#### Scenario: Static partition

- **WHEN** 一个线程用完自己的静态份额而另一个线程空闲
- **THEN** 该线程不能借用空闲份额

#### Scenario: Reserve borrow

- **WHEN** 一个线程超过reserve且其他线程保留空间未使用
- **THEN** 借用不能侵占其他线程未使用的reserve

### Requirement: 目标MC相关CBusy准入

CBusy MUST 只限制匹配`(destination MC, PARTID)`的新事务，不撤回已发事务。

#### Scenario: MC0拥塞

- **WHEN** MC0对PARTID P反馈CBusy且MC1没有反馈
- **THEN** P发往MC1的请求不因MC0反馈被限制

## MODIFIED Requirements

### Requirement: CBusy控制有效OSTD

requester MUST 把延迟到达的CBusy作为匹配`(目标MC, PARTID)`的新事务有效OSTD上限，
同时保留Thread和Core配置上限。

#### Scenario: 多MC反馈隔离

- **WHEN** MC0对PARTID P反馈CBusy且MC1未反馈
- **THEN** P发往MC0的新事务使用MC0 cap，发往MC1的新事务不使用MC0 cap

#### Scenario: CBusy源端阻塞

- **WHEN** 匹配目标MC的PARTID计数达到CBusy上限但Thread和Core仍有空间
- **THEN** 新请求保留在源端，延迟归因到CBusy stall

#### Scenario: 保证基本前向进展

- **WHEN** Level 3 CBusy生效
- **THEN** 有效OSTD至少为1，已发请求和返回路径不受准入门控
