## 背景

当前spec已经要求控制器只能读取授权硬件信号和MPAM监控值，并要求L3 CMIN/CMAX、
MC BMIN/BMAX使用上一周期filtered监控值。现有`MON-003`的更新顺序写成
“计算filtered后执行控制”，容易被实现成同一监控边界刚计算出的filtered立即驱动控制。

## 目标

- 将P2阶段目标收窄为一件事：冻结“监控采样 -> 滤波发布 -> 控制读取 -> 动作生效”的时序语义。
- 明确raw/filtered发布值可用于UI和证据，但控制器读取的必须是上一次边界锁存的control input。
- 修正L3和MC实现，防止同一monitor boundary之后的同timestamp调度读取刚计算出的filtered。
- 增加微测试证明L3 CMIN/CMAX、MC BMIN/BMAX不会出现同周期filtered立即控制。

## 非目标

- 不新增P2专用仿真模式、数据模型或UI通路。
- 不改变raw、filtered、actual现有用户可见曲线含义。
- 不要求控制目标一定达成；过冲和释放延迟仍属于可观察硬件取舍。
- 不扩展NoC QoS、DRAM bank/row/refresh、resctrl/libvirt接口或完整UI工作区。

## 风险

- hard BMAX断言和释放都会增加一个本地监控边界的动作延迟；这是P2刻意冻结的时序语义，
  不是控制失败。
- filtered监控值与control input在UI证据中可能不同，需要用字段名区分“刚发布监控值”和
  “当前控制读取值”。
