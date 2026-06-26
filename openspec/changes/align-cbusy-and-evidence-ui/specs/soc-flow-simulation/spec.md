## MODIFIED Requirements

### Requirement: CBusy控制有效OSTD

requester MUST 把延迟到达的CBusy作为匹配PARTID的新事务有效OSTD上限，
同时保留Thread和Core配置上限。目标MC、来源MC和sample time仅用于路由、完成释放、
来源证据和诊断，不得作为CPU源端限流索引。

#### Scenario: MC0反馈PARTID拥塞

- **WHEN** requester R从返回路径收到PARTID P的CBusy
- **THEN** R中PARTID P的后续新事务 MUST 受该PARTID cap约束
- **AND** P发往任意MC的新事务都受该PARTID cap约束
- **AND** 其他PARTID的新事务 MUST NOT 受该PARTID cap约束
- **AND** MC ID MAY 作为反馈来源和诊断字段导出
