# soc-flow-simulation 规格

## Purpose

定义当前已实现的确定性系统级仿真路径、配置边界、延迟归因、CPU OSTD监控、
控制机制比较和可复现输出契约，作为当前代码行为的机器可验证能力基线。
## Requirements

### Requirement: 阶段命名与PARTID命名消歧

规格、OpenSpec change、测试说明和UI文案 MUST 明确区分阶段命名与MPAM PARTID命名。

#### Scenario: 描述阶段验收

- **WHEN** 文档描述机制可信性、后续增强阶段或计划优先级
- **THEN** 可以使用`P0`、`P1`、`P2`等阶段命名
- **AND** 首次出现时 SHOULD 说明它表示阶段、验收或计划优先级

#### Scenario: 描述MPAM标识

- **WHEN** 文档、测试或UI文案描述MPAM PARTID编号
- **THEN** MUST 写成`PARTID 0`、`PARTID 1`、`PARTID 2`或`PARTID N`
- **AND** MUST NOT 使用`P0`、`P1`、`P2`缩写PARTID

### Requirement: 确定性系统级仿真

配置和随机种子不变时，系统 MUST 确定性地执行离散事件SoC模型。

#### Scenario: 重复相同运行

- **WHEN** 两次仿真使用相同的已校验配置和seed
- **THEN** issued、completed和报告指标 MUST 一致

### Requirement: 可配置多核请求路径

系统 MUST 以因果请求路径建模可配置core、thread、requester、NoC、共享L3/SLC和MC。

#### Scenario: 增加活动requester

- **WHEN** workload使用`per_requester`注入且活动requester增加
- **THEN** offered traffic和共享资源竞争增加，且无需修改源码

### Requirement: 流控延迟归因

系统 MUST 把完成请求延迟分解为NoC、cache、memory queue、memory service和throttle。

#### Scenario: 诊断带宽限制

- **WHEN** hard BMAX延迟请求
- **THEN** 导出指标 MUST 把throttle delay与queue/service delay分开

### Requirement: 可复现输出

系统 MUST 导出resolved config、topology、run summary、每PARTID指标、每MSC指标、
timeline和control trace。

#### Scenario: 完成仿真

- **WHEN** 仿真正常完成且启用输出
- **THEN** MUST 生成JSON、CSV和可选静态HTML报告

### Requirement: P1最小闭环MVP范围

P1 MUST 实现最小闭环MVP，不得扩展为完整SoC仿真。

#### Scenario: P1范围确认

- **WHEN** 规划、实现或验收P1
- **THEN** MUST 聚焦L3 CMAX、MC BMAX和CBusy到RN OSTD三条闭环
- **AND** MUST NOT 把NoC QoS、credit/VC、完整DRAM bank/row/refresh、完整resctrl/libvirt接口、完整UI工作区、自动根因分类、PPA综合评分或所有控制组合测试纳入P1完成条件

### Requirement: P1复用常规数据面和证据链

P1 MUST 复用现有类型化`Transaction`、`MonitorSample`、`ControlEvent`和决策轨迹类型。
当前实现中的决策轨迹类型名为`ControlDecision`；UI或文档可以称为`DecisionTrace`，
但不得新增另一套P1专用决策类型。

#### Scenario: 不新增阶段旁路

- **WHEN** P1场景运行或展示结果
- **THEN** MUST 使用常规仿真模式、常规数据模型和常规UI通路
- **AND** MUST NOT 新增`validation_stage`运行模式、P1专用数据面或P1专用UI通路

#### Scenario: 控制器输入隔离

- **WHEN** P1中的CMAX、BMAX或CBusy相关控制器做决策
- **THEN** MUST 只读取规格授权的监控值、本地执行状态和配置状态
- **AND** MUST NOT 读取actual语义数据作为控制输入

### Requirement: P1三条闭环场景

P1 MUST 跑通L3 CMAX occupancy control、MC BMAX bandwidth control和
CBusy -> RN OSTD source throttling三条场景。

#### Scenario: L3 CMAX occupancy control

- **WHEN** L3发布并保存的control sampled occupancy达到或超过CMAX
- **THEN** 在对应`action_effective_time_ns`之后，该PARTID新增L3 allocation MUST 被限制、旁路或只能自替换
- **AND** actual occupancy MAY 因在途fill、采样误差或交织误差短暂过冲

#### Scenario: MC BMAX bandwidth control

- **WHEN** MC基于63bit累计计数差分发布并保存的control bandwidth超过BMAX
- **THEN** soft BMAX MUST 能改变对应PARTID的MC effective QoS
- **AND** hard BMAX MUST 能产生对应PARTID的hard block
- **AND** 事件 MUST 标明`limit_mode=soft`或`limit_mode=hard`

#### Scenario: CBusy返回RN后源端限流

- **WHEN** MC在完成服务时把CBusy状态采样到RSP或DAT返回旁带
- **THEN** RN收到返回后 MUST 能按该返回事务归因出的PARTID降低effective OSTD
- **AND** 目标MC MUST 只作为反馈来源、路由和诊断字段，不得作为RN源端限流索引
- **AND** 不得影响其他PARTID的effective OSTD

### Requirement: P1成功标准

P1成功 MUST 以控制动作闭环和证据完整性判断，不得要求任意目标必然达成。

#### Scenario: 确定性复现

- **WHEN** 两次运行使用相同配置和seed
- **THEN** 三条P1场景的关键监控、决策、控制事件和结果指标 MUST 确定性复现

#### Scenario: 因果ID完整

- **WHEN** P1导出任一控制事件
- **THEN** 该事件 MUST 能追踪`monitor_sample_id`、`decision_id`和`action_effective_time_ns`

#### Scenario: 控制结果失败不中止

- **WHEN** P1场景出现目标未达、过冲、振荡、控制饱和或不可行目标
- **THEN** MUST 记录为`CONTROL_OUTCOME`
- **AND** MUST NOT 中止仿真

### Requirement: P0 P1时序前置门槛

监控、滤波、控制和动作的双缓冲时序 MUST 作为P0机制可信和P1最小闭环的共同前置门槛。

#### Scenario: P0时序门槛

- **WHEN** P0验证控制机制是否可信
- **THEN** MUST 验证控制器读取的是锁存`control_input`
- **AND** MUST 验证窗口内尚未发布的raw、actual或debug状态不会驱动控制

#### Scenario: P1闭环门槛

- **WHEN** P1验证L3 CMAX、MC BMAX或CBusy闭环
- **THEN** 控制事件 MUST 引用锁存`control_input`对应的monitor sample
- **AND** `action_effective_time_ns` MUST 不早于该control input被锁存的本地边界

### Requirement: 四层监控语义

平台telemetry MUST 区分`actual`、`raw_monitor`、`filtered_monitor`和`control_input`。

#### Scenario: control input语义

- **WHEN** L3或MC导出控制器实际读取的锁存监控值
- **THEN** 对应`MonitorSample.semantic` MUST 为`control_input`
- **AND** MUST NOT 被归类为`actual`或`filtered_monitor`

#### Scenario: latest filtered语义

- **WHEN** L3或MC导出刚发布的滤波监控值
- **THEN** 对应`MonitorSample.semantic` MUST 为`filtered_monitor`
- **AND** L3 occupancy UI MUST 标注为published sampled owner或最新发布sampled-owner
- **AND** MC bandwidth UI MAY 标注为latest filtered bandwidth

#### Scenario: L3 sampled control语义

- **WHEN** L3导出CMIN/CMAX实际读取的抽样占用
- **THEN** 对应`MonitorSample.semantic` MUST 为`control_input`
- **AND** UI MUST 标注为control sampled occupancy或控制输入

### Requirement: 控制结果契约

目标未达、过冲、饱和、不可行或性能恶化 MUST 记录为控制结果，而不是仿真失败。

#### Scenario: CONTROL_OUTCOME字段

- **WHEN** 导出任一控制事件
- **THEN** 事件行 SHOULD 包含稳定的`outcome_state`和`outcome_reason`字段
- **AND** outcome状态 MUST 用于解释目标偏离，不得作为自动中止条件

### Requirement: 控制上下文扩展边界

后续新增控制能力 MUST 通过类型化`ControlContext`读取授权监控样本、资源scope、
上一控制状态和动作生效边界；P1不因此扩展到完整SoC仿真。

#### Scenario: 新控制策略

- **WHEN** 新增NoC QoS、PE侧限流、多MC协同或PMG策略
- **THEN** SHOULD 通过`ControlContext`声明授权输入
- **AND** MUST NOT 直接读取私有actual状态或阶段专用数据面

### Requirement: 独立硬件线程workload

Web配置构建器 MUST 为16线程矩阵中每个启用行生成一个workload，并绑定固定requester。

#### Scenario: 启用全部激励

- **WHEN** 16行全部启用
- **THEN** resolved config包含16个workload并绑定16个不同CPU线程requester

#### Scenario: 关闭一个激励

- **WHEN** 一个激励行被关闭
- **THEN** 不为该requester生成workload，其他映射保持不变

### Requirement: resctrl-like软件组转换

Web配置构建器 MUST 支持可选resctrl-like软件组输入，并在仿真配置生成阶段转换为
现有硬件线程workload标签和MPAM MSC settings table。

#### Scenario: CTRL_MON group映射PARTID

- **WHEN** resctrl-like模式启用且CTRL_MON group有效
- **THEN** 每个CTRL_MON group MUST 映射到一个唯一内部PARTID
- **AND** group的L3/MB `schemata` MUST 转换为对应PARTID的CPBM和MC BMAX设置

#### Scenario: MON group映射PMG

- **WHEN** 某任务或CPU被放入CTRL_MON group下的MON group
- **THEN** 新事务 MUST 使用该CTRL_MON group的PARTID和该MON group的PMG
- **AND** PMG作用域 MUST 限定在同一个PARTID内

#### Scenario: 任务优先于CPU默认组

- **WHEN** 一个硬件线程同时被任务列表和CPU列表覆盖
- **THEN** 显式`tasks`归属 MUST 优先于`cpus_list`
- **AND** 未命中的线程 MUST 使用root group

#### Scenario: 不新增控制器输入

- **WHEN** resctrl-like模式转换完成后运行仿真
- **THEN** 控制器 MUST 仍然只读取现有授权MPAM监控值、本地执行状态和配置状态
- **AND** MUST NOT 读取resctrl UI的验证用actual数据作为控制输入

### Requirement: 激励配置校验

每个启用激励 MUST 只生成一个注入速率字段，并校验PARTID、PMG、size、read ratio、
working set、target、地址模式、依赖模式、到达模式、发射选择和源队列深度。

#### Scenario: 使用MRPS

- **WHEN** 激励选择MRPS
- **THEN** 只生成`injection_rate_mrps`

#### Scenario: 使用Gbps

- **WHEN** 激励选择Gbps
- **THEN** 只生成`injection_rate_gbps`

#### Scenario: Pointer chain兼容预设

- **WHEN** workload使用`workload_type=pointer_chase`
- **THEN** resolved workload MUST 使用`address_pattern=pointer_chase`和`dependency_mode=pointer_chain`

### Requirement: Pointer chain依赖

`dependency_mode=pointer_chain` MUST 保证同一链的下一请求只在上一请求终端返回后生成。

#### Scenario: 同链不并发

- **WHEN** 一个pointer chain workload使用高注入速率和较大OSTD
- **THEN** 同一`stimulus_chain_id`的请求issue时间 MUST 不早于上一请求完成时间

### Requirement: Eligible scan发射选择

`issue_selection=eligible_scan` MUST 只扫描已生成的源队列描述符，不得生成新地址或越过依赖。

#### Scenario: 源队列扫描

- **WHEN** 队首请求被PARTID CBusy或其他源端准入条件限制但后续独立请求可准入
- **THEN** eligible scan MAY 选择后续可准入请求；fifo MUST 不越过队首

### Requirement: Web任务安全上限

构建器 MUST 估算全部启用激励的请求总量，并拒绝超过Web任务上限的配置。

#### Scenario: 总流量过大

- **WHEN** 估算请求数超过2,000,000
- **THEN** MUST 在启动仿真前拒绝任务

### Requirement: 每PARTID CPU OSTD监控

仿真器 MUST 在每个控制周期采样requester的PARTID OSTD，且不引入CPU流水线模型。

#### Scenario: 采样OSTD

- **WHEN** 捕获控制周期
- **THEN** 每个requester/PARTID报告当前值、周期峰值、配置上限、issued/completed和backpressure

#### Scenario: 重置周期峰值

- **WHEN** 一个CPU监控周期结束
- **THEN** 下一周期峰值从当前OSTD开始

### Requirement: CBusy控制有效OSTD

requester MUST 把延迟到达的CBusy作为匹配PARTID的新事务有效OSTD上限，
同时保留Thread和Core配置上限。目标MC仅用于路由、完成释放和诊断，不作为CPU限流索引。

#### Scenario: 多MC反馈按PARTID聚合

- **WHEN** MC0对PARTID P反馈CBusy且MC1未反馈
- **THEN** 收到该反馈的requester对PARTID P的新事务使用PARTID聚合cap
- **AND** P发往MC1的新事务也受该PARTID cap约束

#### Scenario: CBusy源端阻塞

- **WHEN** Core内该PARTID计数达到CBusy上限但Thread和Core仍有空间
- **THEN** 新请求保留在源端，延迟归因到CBusy stall

#### Scenario: 保证基本前向进展

- **WHEN** Level 3 CBusy生效
- **THEN** 有效OSTD至少为1，已发请求和返回路径不受准入门控

#### Scenario: 返回旁带不广播

- **WHEN** 某请求返回到requester R并携带PARTID P的CBusy
- **THEN** 只有R更新PARTID P的反馈状态，其他同PARTID requester MUST 保持原状态

### Requirement: 可复现机制比较

仿真器 MUST 能够派生只改变控制开关、保持workload、topology、duration和seed不变的案例。

#### Scenario: 派生比较案例

- **WHEN** 提交有效配置
- **THEN** 四个派生案例保持非控制输入不变并使用static policy

### Requirement: 确定性机制微测试

仿真器 MUST 支持隔离cache最小/最大和memory bandwidth最小/最大行为的内置workload。

#### Scenario: 重复验证套件

- **WHEN** 两次使用相同参数和seed
- **THEN** 检查结果和证据一致

### Requirement: 目标与效果证据

仿真器 MUST 输出足够的周期证据，用于比较cache、bandwidth、QoS和latency目标与结果。

#### Scenario: 分析完整运行

- **WHEN** 仿真完成
- **THEN** 用户可以直接根据周期快照计算目标符合度

### Requirement: 类型化跨模块事务

仿真器 MUST 使用单一`Transaction`类型在requester、NoC、L3和MC之间传递请求，
并显式保存路由、延迟、完成条件和仲裁结果，禁止组件写入未声明动态属性。

#### Scenario: MC完成一次仲裁

- **WHEN** MC选择一个候选请求
- **THEN** base QoS、effective QoS、aging、BMIN和soft BMAX结果写入声明的仲裁状态

#### Scenario: 保留旧导入路径

- **WHEN** 现有代码从`src.traffic.request`导入`Request`
- **THEN** 得到与`Transaction`相同的权威运行时类型

### Requirement: 类型化监控和控制因果链

每个MSC MUST 发布类型化监控快照和样本，控制动作 MUST 通过稳定ID连接监控样本、
决策、动作生效时间及后续导出记录。

#### Scenario: 慢速策略更新设置

- **WHEN** policy根据一个控制周期的指标修改MPAM设置
- **THEN** control event保存monitor sample ID、decision ID、old/new state和生效时间

### Requirement: 组件能力声明

每个可运行组件 MUST 声明输入输出、能力、所需监控、动作、验证钩子、近似和不兼容组合。

#### Scenario: 注册当前组件

- **WHEN** Simulation完成NoC、L3和MC构建
- **THEN** registry校验唯一ID并导出全部组件能力

### Requirement: 两级CPU OSTD

每个硬件线程 MUST 维护独立thread OSTD，属于同一core的两个线程 MUST 共享core OSTD池。

#### Scenario: 两线程竞争共享池

- **WHEN** 两个SMT线程的thread OSTD之和达到core limit
- **THEN** 后续新事务留在源端，任一事务完成后可继续准入

### Requirement: 可配置Core OSTD策略

Core OSTD池 MUST 支持shared、static_partition和reserve_borrow，并在eligible pending线程间
使用确定性work-conserving round-robin。

#### Scenario: Static partition

- **WHEN** 一个线程用完自己的静态份额而另一个线程空闲
- **THEN** 该线程不能借用空闲份额

#### Scenario: Reserve borrow

- **WHEN** 一个线程超过reserve且其他线程保留空间未使用
- **THEN** 借用不能侵占其他线程未使用的reserve

### Requirement: PARTID相关CBusy准入

CBusy MUST 只限制收到反馈的requester中匹配PARTID的新事务，不撤回已发事务。
目标MC MUST NOT 作为CPU源端限流索引。

#### Scenario: MC0反馈PARTID拥塞

- **WHEN** MC0对PARTID P反馈CBusy且MC1没有反馈
- **THEN** 收到反馈的requester内PARTID P后续请求都会受PARTID cap约束
- **AND** 其他PARTID请求不受该反馈影响

### Requirement: 三条双向Bufferless Ring

系统 MUST 使用独立REQ、RSP和DAT双向bufferless ring。Ring内部flit MUST 每个hop周期
前进，且MUST NOT按PARTID或QoS仲裁。

#### Scenario: 最短方向

- **WHEN** source到destination的两个方向距离不同
- **THEN** flit选择hop数更少的方向

#### Scenario: 等距方向

- **WHEN** 两个方向距离相同
- **THEN** 使用配置的固定tie方向且重复运行结果一致

### Requirement: 目的端拒绝后绕行

flit到达目标节点但endpoint不能接收时 MUST 继续移动并在下一周再次尝试下Ring。

#### Scenario: MC Buffer暂满

- **WHEN** REQ flit到达MC而MC不能接收
- **THEN** flit不丢失、不停止且记录failed ejection和完整绕环

### Requirement: REQ注入参与CPU准入

CPU MUST 在分配transaction ID和OSTD前确认REQ Ring源link有可用槽。

#### Scenario: REQ Ring满

- **WHEN** Thread、Core和CBusy允许但REQ源link没有空槽
- **THEN** 待发描述保留在源端并记录`req_ring` stall，不增加OSTD

### Requirement: DAT逐Flit传输

DAT MUST 按配置flit大小拆分、独立注入和移动，并在全部flit下Ring后完成transaction。

#### Scenario: 64B DAT使用16B flit

- **WHEN** 一个64B read data返回
- **THEN** 生成4个DAT flit且只在4个flit全部下Ring后释放CPU OSTD

### Requirement: 真实L3 Tag和替换

L3 MUST 使用真实set/tag/way状态决定hit/miss，并支持确定性LRU和PLRU。

#### Scenario: 重复访问已fill地址

- **WHEN** 一个地址miss、完成fill后再次访问且未被驱逐
- **THEN** 第二次访问命中同一tag且不访问MC

### Requirement: L3 MSHR和同Line合并

L3 MUST 支持可配置的同一cache line并发read miss合并；默认配置 MUST 关闭合并，以保留
每笔miss对MSHR、MC和流控路径的独立压力。

#### Scenario: 默认关闭合并

- **WHEN** `merge_same_line_misses`未显式开启，且PARTID 0先miss、PARTID 1在fill前read同一line
- **THEN** 两个read miss MUST 保持独立MSHR/MC请求路径
- **AND** 后返回fill发现line已存在时 MUST 记录redundant fetch证据且不改写line owner

#### Scenario: 显式开启合并

- **WHEN** `merge_same_line_misses`显式开启，且PARTID 0先miss、PARTID 1在fill前read同一line
- **THEN** 只发一个MC请求，fill owner为PARTID 0，两个请求分别返回完成

### Requirement: Fill Buffer和返回完成

MC DAT MUST 在L3 fill buffer可接收时下Ring，完成fill后才向CPU返回并释放OSTD。

#### Scenario: Fill Buffer满

- **WHEN** DAT到达L3且fill buffer没有空entry
- **THEN** DAT继续在Ring绕行且不提前完成MSHR waiter

### Requirement: MC共享Buffer全候选

MC MUST 让共享buffer中所有valid、ready且未被hard BMAX或ordering阻塞的entry参与QoS比较。

#### Scenario: 高QoS位于非队首Slot

- **WHEN** 一个高QoS ready entry位于共享buffer后部
- **THEN** 它仍参与本次最高QoS选择

### Requirement: 同Line最小顺序

MC MUST 允许同line read/read重排，并阻止任何包含write的较新同line entry越过较老entry。

#### Scenario: Write后Read

- **WHEN** 较老write和较新read访问同一line
- **THEN** 较新read在write离开buffer前不可调度

### Requirement: Rotating Slot仲裁

同最高QoS候选 MUST 从上次grant slot之后旋转扫描选择，不使用enqueue时间作为默认比较。

#### Scenario: 相同QoS持续竞争

- **WHEN** 多个slot持续保持相同最高QoS
- **THEN** grant位置按slot轮转且确定性前进

### Requirement: 可配MC地址交织

仿真 MUST 支持linear和XOR地址交织，并在CPU发射前确定目标MC。

#### Scenario: 相同配置复现

- **WHEN** 两次仿真使用相同地址、granularity、XOR shift和MC数量
- **THEN** 每个地址映射到相同MC
