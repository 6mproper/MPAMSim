# soc-flow-simulation 规格

## Purpose

定义当前已实现的确定性系统级仿真路径、配置边界、延迟归因、CPU OSTD监控、
控制机制比较和可复现输出契约，作为当前代码行为的机器可验证能力基线。
## Requirements
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

### Requirement: 独立硬件线程workload

Web配置构建器 MUST 为16线程矩阵中每个启用行生成一个workload，并绑定固定requester。

#### Scenario: 启用全部激励

- **WHEN** 16行全部启用
- **THEN** resolved config包含16个workload并绑定16个不同CPU线程requester

#### Scenario: 关闭一个激励

- **WHEN** 一个激励行被关闭
- **THEN** 不为该requester生成workload，其他映射保持不变

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

- **WHEN** 队首请求被目标MC/PARTID CBusy限制但后续独立请求可准入
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

requester MUST 把延迟到达的CBusy作为匹配`(目标MC, PARTID)`的新事务有效OSTD上限，
同时保留Thread和Core配置上限。

#### Scenario: 多MC反馈隔离

- **WHEN** MC0对PARTID P反馈CBusy且MC1未反馈
- **THEN** P发往MC0的新事务使用MC0 cap，发往MC1的新事务不使用MC0 cap

#### Scenario: CBusy源端阻塞

- **WHEN** 匹配目标MC的PARTID计数达到CBusy上限但Thread和Core仍有空间
- **THEN** 新请求保留在源端，延迟归因到CBusy stall

#### Scenario: 保证基本前向进展

- **WHEN** Level 3 CBusy生效
- **THEN** 有效OSTD至少为1，已发请求和返回路径不受准入门控

#### Scenario: 返回旁带不广播

- **WHEN** 某请求返回到requester R并携带`(MC0, PARTID P)` CBusy
- **THEN** 只有R更新MC0/P的反馈状态，其他同PARTID requester MUST 保持原状态

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

### Requirement: 目标MC相关CBusy准入

CBusy MUST 只限制匹配`(destination MC, PARTID)`的新事务，不撤回已发事务。

#### Scenario: MC0拥塞

- **WHEN** MC0对PARTID P反馈CBusy且MC1没有反馈
- **THEN** P发往MC1的请求不因MC0反馈被限制

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

默认配置下，同一cache line的并发read miss MUST 合并为一个MC请求，并保留每个waiter的
独立CPU OSTD。

#### Scenario: 两个PARTID访问同一未缓存Line

- **WHEN** P0先miss且P1在fill前read同一line
- **THEN** 只发一个MC请求，fill owner为P0，两个请求分别返回完成

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
