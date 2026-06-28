## 背景

MC `actual`原先直接显示单个控制窗口内完成服务的bytes/interval。
在128ns等短窗口下，按PARTID分桶后的完成事件会强烈量化，视觉上容易从高值跳到0，
不利于用户识别控制效果趋势。

## 目标

- 控制效果页和控制总览页的MC `actual`显示为尾随moving average。
- moving average只使用当前窗口和过去窗口，不使用未来样本。
- 尾部`final:*`或不完整窗口仍不参与MC actual曲线和autoscale。
- 保留原始单窗口`achieved_bandwidth_gbps`数据，不让控制器读取actual。

## 非目标

- 不修改MC raw/filter/control input算法。
- 不新增仿真运行模式或后端控制路径。
