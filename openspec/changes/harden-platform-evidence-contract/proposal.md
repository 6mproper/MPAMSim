## 背景

P0/P1已经把机制可信、最小闭环和目标未达继续运行定义清楚；P2也实现了
监控、滤波、控制和动作的双缓冲时序。但当前平台契约仍有三个风险：

- `control_input`不是一等telemetry语义，容易被误归为actual；
- UI和部分旧OpenSpec仍把latest filtered误写成控制读取值；
- `CONTROL_OUTCOME`和内部MSC控制动作没有稳定统一证据通路。

这些风险会让系统流控和MPAM验证平台在后续扩展控制能力时重新走向私有字段和局部解释。

## 目标

- 将时序冻结明确为P0/P1共同前置门槛，而不是后置增强。
- 固定四层监控语义：`actual`、`raw_monitor`、`filtered_monitor`、
  `control_input`。
- 让`control_input`进入`MonitorSample.semantic`、CSV和UI。
- 将MC BMIN/BMAX和L3 CMIN/CMAX的内部状态切换复用现有`ControlEvent`通路。
- 给`ControlEvent`增加稳定`CONTROL_OUTCOME`字段。
- 在spec中定义未来控制策略使用的`ControlContext`边界，但不强制一次性重构所有policy。
- 清理已知旧语义：filtered不再表示控制实际读取值；它表示最新发布滤波监控值。

## 非目标

- 不新增`validation_stage`、阶段专用数据面或专用UI通路。
- 不扩展完整NoC QoS、DRAM bank/row/refresh、resctrl/libvirt或OS接口。
- 不把目标达成作为自动验收条件。
- 不重写现有仿真框架；本次只补平台级证据契约和必要实现。

## 风险

- UI多一条control input曲线，默认视图必须保持紧凑，raw和latest filtered可以按需显示。
- 内部控制事件可能增加control trace行数，因此L3先记录状态切换事件，不逐请求记录每一次denial。
