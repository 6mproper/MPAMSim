## MODIFIED Requirements

### Requirement: CBusy控制有效OSTD

requester MUST 把延迟到达的CBusy作为匹配PARTID的新事务有效OSTD上限，同时保留Thread和Core配置上限。
目标MC仅用于路由、完成释放和诊断，不作为CPU限流索引。

#### Scenario: 多MC反馈按PARTID聚合

- **WHEN** MC0对PARTID P反馈CBusy且MC1未反馈
- **THEN** 收到该反馈的requester对PARTID P的新事务使用PARTID聚合cap
- **AND** P发往MC1的新事务也受该PARTID cap约束

#### Scenario: CBusy源端阻塞

- **WHEN** Core内该PARTID计数达到CBusy上限但Thread和Core仍有空间
- **THEN** 新请求保留在源端，延迟归因到CBusy stall

#### Scenario: 保证基本前向进展

- **WHEN** Level 3 CBusy生效
- **THEN** 有效OSTD至少为1，已发请求和返回路径不受准入门控

#### Scenario: 返回旁带不广播

- **WHEN** 某请求返回到requester R并携带PARTID P的CBusy
- **THEN** 只有R更新PARTID P的反馈状态，其他同PARTID requester MUST 保持原状态

### Requirement: PARTID相关CBusy准入

CBusy MUST 只限制收到反馈的requester中匹配PARTID的新事务，不撤回已发事务。
目标MC MUST NOT 作为CPU源端限流索引。

#### Scenario: MC0反馈PARTID拥塞

- **WHEN** MC0对PARTID P反馈CBusy且MC1没有反馈
- **THEN** 收到反馈的requester内PARTID P后续请求都会受PARTID cap约束
- **AND** 其他PARTID请求不受该反馈影响
