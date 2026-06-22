## 背景

总体规格要求先建立稳定接口，再按依赖顺序替换数据面。当前`Request`字段不完整，
路由状态由不同组件直接写入，MC仲裁使用动态属性，monitor snapshot没有schema，
控制记录也缺少稳定ID和监控样本关联。

## 目标

- 让跨模块状态只通过类型对象传递。
- 消除请求动态属性。
- 让监控样本、控制决策和动作可以稳定关联。
- 让组件声明能力和限制，配置阶段可以发现不兼容组合。
- 保持现有仿真行为、Web API和CSV主要列兼容。

## 非目标

- 本change不实现bufferless ring。
- 本change不实现真实全set/tag/way L3。
- 本change不替换BMIN/BMAX算法。
- 本change不实现完整CHI flit。

## 设计

### Transaction

`Transaction`直接包含：

- transaction和parent ID；
- requester、core、thread、PARTID和PMG；
- source、destination、cache和MC路由；
- address、line address、size、operation和request class；
- issue time和completion condition；
- 类型化延迟状态；
- 类型化MC仲裁结果；
- cache outcome。

`Request`只作为导入兼容别名，不建立第二套对象。

### Monitor

组件返回`MonitorSnapshot`，其中保存资源类型、实例、时间、周期、sample ID和原始payload。
快照把顶层、每PARTID及每`(PARTID, PMG)`标量转换为`MonitorSample`。
collector继续生成现有`msc_rows`，同时保存规范化样本并导出`monitor_samples.csv`。

### Control

policy返回`ControlDecision`。Simulation应用设置后生成`ControlEvent`，记录：

- event和decision ID；
- monitor sample ID；
- old/new state；
- action effective time；
- resource、PARTID、field和reason。

CBusy反馈到达也生成同一事件类型。

### 接口和能力

定义`EndpointPort`、`RingTransport`、`CacheLookupPipeline`、`ReplacementPolicy`、
`MshrTable`、`McReadinessPolicy`、`McScheduler`、`MonitorSource`、`ControlPolicy`
和`ValidationHook`协议。

每个当前组件声明`CapabilityDescriptor`，明确输入、输出、能力、动作、监控、验证钩子、
近似和不兼容能力。`ComponentRegistry`检查重复ID及不兼容组合，并导出能力清单。

## 兼容策略

- 现有模块仍可从`src.traffic.request`导入`Request`。
- Web继续消费字典投影。
- 现有`control_trace.csv`保留列，并增加稳定ID和因果字段。
- 新增接口不引入第二套数据通路。
