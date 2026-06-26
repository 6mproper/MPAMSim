## 背景

当前控制总览已经支持target、control input、published、raw、actual和控制事件多层曲线，
但raw sampled-owner、published sampled-owner和control input在L3占用稳定时容易重叠，
主视图不够聚焦。同时主spec仍残留旧的MC+PARTID CBusy源端限流表述，
与已经确认的低PPA约束不一致：CPU/L3只感知返回事务归因出的PARTID和CBusy，不使用MC ID作为限流索引。

## 目标

- 控制总览默认突出目标带、control input、actual和控制事件。
- raw sampled-owner和published sampled-owner保留为可选高级证据，不默认干扰主视图。
- 主spec和OpenSpec统一CBusy语义：MC按PARTID生成CBusy；CPU/L3按PARTID聚合响应；MC ID仅用于路由、释放、来源证据和诊断。
- 清理L3 occupancy的“filtered”旧词，统一到raw sampled-owner、published sampled-owner、control input和actual。
- 明确监控边界发布、控制锁存和动作生效顺序，防止同窗口偷跑。

## 非目标

- 不把CPU/L3限流改成`(target MC, PARTID)`索引。
- 不删除raw/published证据曲线或导出字段。
- 不改变L3/MC核心控制算法。
