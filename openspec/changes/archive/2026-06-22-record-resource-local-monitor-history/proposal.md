## Why

当前L3和MC在各自本地监控周期（256拍）更新filtered状态，但只在全局`control_interval_ns`边界通过`monitor_snapshot()`导出快照。本地周期之间的中间状态、trigger条件和过渡轨迹被丢弃，控制决策只能看到下采样后的聚合。离散保存每本地周期全部16个PARTID的状态样本，并用稳定因果ID连接observation→decision→action→result，消除采样窗口损失。

## What Changes

- L3和MC每个本地监控周期发布所有16个PARTID的periodic state sample（包括0活动PARTID）
- 每个sample标记`observation_id`、`resource_id`、`local_cycle`和`partid`
- 控制决策延长`ControlDecision`，支持`observation_id`→`decision_id`→`action_id`因果链
- `ControlEvent`增加`cause_id`，可追踪action生效后的后续observation
- MetricsCollector扩展`monitor_sample_rows`，离散保存每本地周期所有PARTID样本
- 保留全局`capture_interval`聚合，但local history独立于全局周期

## Capabilities

### Modified Capabilities

- `soc-flow-simulation`: "每PARTID CPU OSTD监控"扩展为"每PARTID资源本地监控历史"；增加因果ID链接的monitor→decision→action tracking requirement
- `interactive-simulation-console`: Web证据时间线支持显示因果链和离散本地采样

## Impact

- `src/contracts/telemetry.py`: MonitorSample增加`observation_id`、`cause_id`字段；ControlEvent增加`cause_id`
- `src/cache/cache_msc.py`: `_publish_bandwidth_monitor`改为发布每PARTID离散sample而非仅更新内部状态
- `src/ddr/memctrl.py`: 同样改为发布离散sample
- `src/monitor/collector.py`: 增加`record_local_sample`方法，保存离散样本
- `src/web/server.py`/`static/`: 时间线支持因果链可视化
