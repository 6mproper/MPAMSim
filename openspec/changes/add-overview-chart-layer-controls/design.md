## 设计

### UI

在控制总览工具栏增加“曲线”显示层配置：

- 目标带：显示 CMIN/CMAX 或 BMIN/BMAX 范围；
- control input：显示MPAM控制实际读取的锁存监控值；
- latest filtered：显示最新发布的滤波监控值，默认关闭；
- actual：显示物理实际 L3 占比或 MC 实际服务带宽；
- raw：显示未滤波 raw 采样；
- 控制事件：显示控制动作所在时间点的事件标记。

该配置作用于控制总览中的 L3 和 MC 两个图，避免分别重复配置导致界面更拥挤。

### 状态

前端维护 `overviewChartLayers` 状态。默认：

```text
targetBand = true
controlInput = true
filtered = false
actual = true
raw = false
events = true
```

用户勾选变化后立即重绘控制总览，不触发 `/api/jobs`，不改变当前仿真数据。

### 图例

图例只显示当前已开启的显示层。raw 不再由单独“显示raw采样误差”开关控制，而作为统一显示层的一项。

### 解释窗口

控制总览中的曲线层选项必须有独立`data-help`解释。算法说明窗口采用和普通字段提示一致的紧凑格式：

- 使用短标签和值的连续文本；
- 不使用大段分区卡片；
- 默认宽度接近普通tooltip，内容过长时局部滚动；
- 保留点击固定和关闭能力，但不遮挡主要图表区域。
