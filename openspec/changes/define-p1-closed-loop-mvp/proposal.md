## 背景

P0已经定义为机制可信性验收。P1需要在不扩展完整SoC仿真的前提下，
跑通最小闭环MVP，证明关键控制机制可以沿统一数据面、监控、决策和事件链路闭环。

## 修改目标

- 明确P1目标是最小闭环MVP，不是完整SoC仿真扩展。
- 固化P1必须跑通的三条场景：
  1. L3 CMAX occupancy control；
  2. MC BMAX bandwidth control；
  3. CBusy -> RN OSTD source throttling。
- 明确P1必须复用现有`Transaction`、`MonitorSample`、`ControlEvent`、
  决策轨迹类型和常规UI/数据通路。当前代码中的决策轨迹类型名为`ControlDecision`；
  UI或文档可称`DecisionTrace`，但不得新增另一套P1专用类型。
- 明确P1禁止新增`validation_stage`模式、P1专用数据面或P1专用UI通路。
- 明确控制器不得读取actual语义数据。
- 明确P1非目标和成功标准。

## 非目标

P1不实现：

- NoC QoS；
- credit/VC；
- 完整DRAM bank/row/refresh；
- 完整resctrl/libvirt接口；
- 完整UI工作区；
- 自动根因分类；
- PPA综合评分；
- 所有控制组合测试。

## 风险

- CMAX和BMAX都使用上一发布监控值，天然存在过冲和恢复延迟；P1不得把这些现象误判为仿真失败。
- CMAX实际occupancy可能因为在途fill、采样误差和交织误差短暂偏离目标；P1判断应聚焦控制动作是否生效。
- BMAX soft和hard语义不同，验收必须区分effective QoS demotion和hard block。
