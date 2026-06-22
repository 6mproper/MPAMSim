## MODIFIED Requirements

### Requirement: CBusy控制有效OSTD

requester MUST 把随RSP或最后一个DAT flit返回携带的CBusy作为匹配`(目标MC, PARTID)`的新事务有效OSTD上限，
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

#### Scenario: CBusy随RSP返回更新

- **WHEN** MC完成write请求并采样CBusy Level 2
- **THEN** RSP flit携带`carry_cbusy_level=2`返回RN，RN更新`(MC0, PARTID P)`本地表为Level 2

#### Scenario: CBusy随最后DAT flit返回更新

- **WHEN** MC完成read请求（4个DAT flit）并采样CBusy Level 1
- **THEN** 仅最后一个DAT flit到达时更新RN本地表，前3个flit不触发更新

#### Scenario: 无返回时保持陈旧状态

- **WHEN** CBusy Level从2降为0但目标PARTID无新请求发往该MC
- **THEN** RN保持Level 2直至有新返回携带Level 0更新

### Requirement: 目标MC相关CBusy准入

CBusy MUST 只限制匹配`(destination MC, PARTID)`的新事务，不撤回已发事务。
CBusy通过RSP/DAT返回flit携带，反馈延迟等于事务返回延迟。

#### Scenario: MC0拥塞

- **WHEN** MC0对PARTID P反馈CBusy且MC1没有反馈
- **THEN** P发往MC1的请求不因MC0反馈被限制

#### Scenario: 已发事务不受新反馈影响

- **WHEN** RN收到携带更高CBusy level的返回后已有outstanding事务
- **THEN** 已发事务的OSTD不被撤回，继续完成
