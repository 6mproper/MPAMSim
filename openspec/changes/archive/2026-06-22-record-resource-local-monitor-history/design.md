## Context

当前监控采集链：L3/MC本地周期更新→全局`capture_interval`→`monitor_snapshot()`一次性导出并reset计数器。本地周期之间的逐周期状态不可见。控制决策只能基于全局间隔的聚合数据，无法关联到具体的本地监控周期。

目标：分离"本地周期采样存储"和"全局间隔聚合"，每个本地周期离散保存所有PARTID的状态，并用稳定因果ID串起observation→decision→action→effect。

## Goals / Non-Goals

**Goals:**
- L3和MC每本地监控周期发布discrete `MonitorSample`（16 PARTID × N metrics）
- 每个sample带`observation_id`，全局唯一
- `ControlDecision`保存`observation_id`（触发决策的监控采样）
- `ControlEvent`保存`decision_id`、`action_id`和`cause_id`
- disabled PARTID记录null/absent而非0
- 相同seed+config生成相同observation_id序列

**Non-Goals:**
- 不改变本地监控周期长度或滤波算法
- 不改变全局`capture_interval`聚合逻辑
- 不改变Web现有图表布局（因果链视图为后续步骤3的范围）

## Decisions

### 1. observation_id格式：`obs:<resource_id>:<local_cycle>`

基于`resource_id`（如`mc0`、`l3_cache`）和单调递增的`local_cycle`计数。
`local_cycle = clock_now / monitor_period_cycles`。确定性且全局唯一。

### 2. 离散sample直接写入MetricsCollector

L3/MC在`_publish_bandwidth_monitor`中调用`collector.record_local_sample()`而非仅更新内部状态。Collector扩展`monitor_sample_rows`保存这些离散样本，独立于全局capture。

### 3. 因果链字段

`ControlDecision`增加`observation_id: str`。
`ControlEvent`增加`cause_id: Optional[str]`，指向触发本次action的observation。
action_id = `action:<decision_id>`，自动推导。

### 4. 0活动和disabled PARTID处理

disabled PARTID采样`value=null`、`semantic=control_state`。
0活动但enabled PARTID采样实际值（raw=0, filtered可能非零因历史）。
统一采集，UI可按需过滤。

## Risks / Trade-offs

- **存储增长** → 每周期~64 samples（16 PARTID × 4 metrics），短期仿真可控；长期可通过UI过滤
- **相同seed确定性** → 所有ID基于单调计数器，确定性与原逻辑一致
