## 背景

MC带宽图中的`raw monitor`、`latest filtered BW`和`control input`都是监控边界发布或锁存的离散状态。
当前控制台用普通折线连接离散点，视觉上会把锁存寄存器值误读成连续缓升。

## 目标

- 在控制效果页和控制总览页，把MC `raw monitor`、`latest filtered BW`和`control input`绘制为阶梯线。
- 保持MC `actual`为普通服务实际曲线，表示区间内完成服务统计。
- 不修改MC监控、滤波或控制算法。

## 非目标

- 不改变L3图表口径。
- 不新增仿真数据字段或控制模式。
