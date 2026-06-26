## 设计

### MC时钟位置

`mc_clock_mhz`属于MC本地资源时钟，移动到SoC页签Memory Controller分组。策略页保留监控周期、history/current权重、带宽滞回和QoS aging等控制算法参数。

### 能力摘要

能力摘要是UI辅助解释，不参与仿真配置。计算规则：

- 多核：根据当前硬件线程激励计算offered带宽；MRPS按`MRPS * request_size_bytes * 0.008`换算为Gbps；同时显示Thread/Core OSTD形成的聚合并发上限。
- L3：显示容量，并用`实例数 * lookup并发槽 * line bytes * 8 / hit_latency_ns`估算全hit lookup峰值Gbps；同时显示监控周期ns。
- NoC：显示三条双向bufferless ring的DAT等效槽位能力，按`3 channels * 2 directions * node_count * slots * flit_bytes * 8 / hop_delay_ns`估算聚合运输Gbps，并显示hop延迟。
- MC：显示每MC和系统总带宽，按`MC数 * 每MC通道数 * 单通道Gbps`计算；同时显示MC监控周期ns。

### 更新机制

`fillForm`、依赖参数clamp、配置input/change以及激励表变化都会刷新摘要。摘要行使用`data-help`说明计算边界，避免被误解为RTL精确带宽。
