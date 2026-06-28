## 背景

MC带宽图中的`actual`来自当前snapshot区间内完成服务的bytes除以区间时间。
当仿真结束时间不是`control_interval_ns`整数倍时，最终`final` snapshot可能只有几个ns。
少量请求在该短窗口完成会被换算成很大的瞬时Gbps，拉高图表纵轴并误导用户判断控制效果。

## 目标

- 保留MC原始snapshot证据，包括`interval_ns`和真实`achieved_bandwidth_gbps`。
- 在控制效果和控制总览的MC带宽图中，尾部不完整窗口的`actual`不参与曲线和纵轴缩放。
- 在表格和概览卡片中把该值标记为尾部窗口不参与，而不是显示成有效控制结果。

## 非目标

- 不修改MC控制算法、BMIN/BMAX/CBusy输入或后端统计值。
- 不删除原始监控数据，不改变CSV/report中的证据字段。
