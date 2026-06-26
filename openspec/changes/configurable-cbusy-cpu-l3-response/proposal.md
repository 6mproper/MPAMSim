## 背景

当前模型已经由MC按每PARTID压力生成CBusy，并随RSP/DAT返回到CPU源端。
但旧规格和实现把CPU响应索引定义为`(目标MC, PARTID)`，这要求CPU保存并参与目标MC维度的控制状态。
我们讨论后认为这不符合低PPA硬件抽象：CPU和L3不应依赖MC ID或issue time做控制，只需要通过返回事务/TxnID/MSHR本地上下文识别PARTID，并感知CBusy档位。

同时，L3之前没有响应CBusy。为了验证“MC反馈不仅能压CPU源头，也能在中间缓存入口降低后续miss压力”，需要把CPU和L3响应做成可独立配置的动作开关。

## 目标

- 增加CPU响应CBusy开关：关闭时仍可观察MC返回CBusy事件，但CPU effective OSTD不收紧。
- 增加L3响应CBusy开关：开启时L3按返回MSHR owner归因PARTID，限制同PARTID新miss的MSHR分配。
- CPU和L3的响应动作按PARTID聚合；目标MC只保留为路由、释放和诊断字段，不作为源端限流索引。
- 保留常规`Transaction`、`MonitorSample`、`ControlEvent`通路，不新增阶段专用数据面或UI通路。
- 更新UI配置和点击说明，使用户能区分MC detector、CPU响应和L3响应。

## 非目标

- 不新增L2 CBusy响应。
- 不新增广播式CBusy控制网络。
- 不改变MC BMAX/BMIN/QoS调度算法。
- 不实现完整CHI CBusy编码、credit、VC或一致性。
