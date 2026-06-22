## 为什么

当前仿真请求对象混合保存路由、延迟和组件私有决策，MC还通过`request._mc_*`
动态属性向监控路径传递QoS结果。组件监控直接返回无约束字典，控制记录也无法稳定连接
监控样本、决策和动作。这些做法会阻碍NoC、L3和MC的原位替换，并违反总体规格
`REQ-001`、`MON-002`和`IMPL-002`。

## 修改内容

- 新增类型化`Transaction`，显式保存身份、路由、延迟、完成条件和MC仲裁结果。
- 保留`Request`导入兼容名，但运行时权威类型只有`Transaction`。
- 新增`MonitorSnapshot`、`MonitorSample`、`ControlDecision`和`ControlEvent`。
- 组件监控改为返回类型化快照，collector继续投影现有Web/CSV行并新增规范化样本导出。
- 去除MC在请求对象上写入动态属性的行为。
- 新增接口协议族和组件能力声明、注册及组合校验。
- 输出组件能力清单和类型化监控样本。

## 影响能力

### 修改能力

- `soc-flow-simulation`：请求、监控、控制和组件接口改为类型化契约。
- `interactive-simulation-console`：保持现有API投影，不直接读取组件私有状态。

## 影响范围

- 新增`src/contracts/`和组件注册模块。
- 修改traffic、NoC、L3、MC、collector、policy和simulation连接路径。
- 不在本change中替换旧NoC、概率L3或token bucket算法。
