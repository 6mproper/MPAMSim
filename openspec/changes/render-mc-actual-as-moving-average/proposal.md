## 背景

MC `actual`曾被显示为尾随moving average，以降低128ns等短窗口下按PARTID分桶导致的视觉抖动。
但这会混淆`actual`验证语义：用户需要看到完整统计窗口内真实服务带宽，而不是前端平滑后的趋势值。

## 目标

- 控制效果页和控制总览页的MC `actual`默认显示完整统计窗口raw actual bandwidth。
- actual moving average保留为独立可选趋势层，必须标注为`actual MA`，默认关闭。
- moving average只使用当前窗口和过去有效窗口，不使用未来样本。
- 尾部`final:*`或不完整窗口仍不参与MC actual曲线和autoscale。
- 保留原始单窗口`achieved_bandwidth_gbps`数据，不让控制器读取actual或actual MA。

## 非目标

- 不修改MC raw/filter/control input算法。
- 不新增仿真运行模式或后端控制路径。
