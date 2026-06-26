## 背景

历史上模型结论分散在`docs/Current_Model_SPEC.md`、`openspec/specs/`和多个`openspec/changes/`中。
这种方式适合快速演进，但后续继续由用户和AI共同修改时，容易出现同一机制在多份规格中重复和冲突。

## 目标

- 明确`docs/Current_Model_SPEC.md`是唯一长期主规格。
- OpenSpec change只记录变更动机、增量要求和验收任务。
- `openspec/specs/`只保留机器校验所需的requirement摘要。
- 新行为合入后必须把稳定结论同步回主规格。

## 非目标

- 不删除历史OpenSpec change。
- 不把OpenSpec流程替换掉。
- 不在本次重写所有历史文档。
