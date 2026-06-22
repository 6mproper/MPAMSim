## 1. 稳定因果ID基础

- [x] 1.1 MonitorSample增加`observation_id: str = ""`和`cause_id: Optional[str] = None`
- [x] 1.2 ControlDecision增加`observation_id: str = ""`
- [x] 1.3 ControlEvent增加`cause_id: Optional[str] = None`
- [x] 1.4 to_row()方法同步输出新字段

## 2. L3每本地周期离散采样

- [x] 2.1 L3增加`local_cycle`计数器，每监控周期递增
- [x] 2.2 L3 `_publish_bandwidth_monitor`改为生成16个PARTID的MonitorSample并写入collector
- [x] 2.3 disabled PARTID输出null值、semantic=control_state
- [x] 2.4 observation_id格式: `obs:<cache_id>:<local_cycle>:<partid>:<metric>`

## 3. MC每本地周期离散采样

- [x] 3.1 MC增加`local_cycle`计数器
- [x] 3.2 MC `_publish_bandwidth_monitor`改为生成16个PARTID的MonitorSample并写入collector
- [x] 3.3 CBusy等控制状态作为独立metric采样
- [x] 3.4 observation_id格式: `obs:<mc_id>:<local_cycle>:<partid>:<metric>`

## 4. MetricsCollector扩展

- [x] 4.1 增加`record_local_sample(sample: MonitorSample)`方法
- [x] 4.2 `monitor_sample_rows`直接追加离散sample（不限于全局capture）
- [x] 4.3 `capture_interval`继续聚合但不再清空离散已保存的数据

## 5. 因果链传播

- [x] 5.1 `Simulation._control_interval`中，policy决策时传入`observation_id`
- [x] 5.2 `ControlDecision.with_context`保存`observation_id`
- [x] 5.3 `ControlEvent`创建时保存`cause_id`（指向前一observation）

## 6. Web离散采样过滤

- [x] 6.1 新增按resource_id、PARTID、semantic的过滤控件
- [x] 6.2 离散采样点按semantic着色（actual绿、raw蓝、filtered橙、state灰）
- [x] 6.3 保留全局capture聚合视图作为默认

## 7. 验证

- [x] 7.1 测试所有16个PARTID每本地周期都有记录
- [x] 7.2 测试disabled PARTID值为null
- [x] 7.3 测试相同seed+config生成相同observation_id序列
- [x] 7.4 测试监控采集不改变调度结果（issued/completed数量不变）
- [x] 7.5 运行完整回归pytest
