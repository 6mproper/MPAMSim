## ADDED Requirements

### Requirement: 主规格唯一事实来源

项目 MUST 使用`docs/Current_Model_SPEC.md`作为唯一长期主规格。OpenSpec change MUST 只记录变更提案、
差异需求和验收任务；稳定行为合入后 MUST 同步回主规格。

#### Scenario: 合入行为变更

- **WHEN** 行为变更完成实现和验证
- **THEN** 稳定模型事实 MUST 写入`docs/Current_Model_SPEC.md`
- **AND** OpenSpec change MUST NOT 成为唯一长期事实来源

#### Scenario: 读取模型规格

- **WHEN** 用户或AI工具需要理解当前整体模型
- **THEN** SHOULD 优先读取`docs/Current_Model_SPEC.md`
- **AND** SHOULD 只把OpenSpec change作为未合入或历史变更记录
