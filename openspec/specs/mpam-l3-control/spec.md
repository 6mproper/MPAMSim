# mpam-l3-control 规格

## Purpose

定义当前已实现的16-PARTID L3/SLC分配控制、独立控制开关、有界请求队列、
比例校验和低成本近似set/way监控，作为当前cache MSC能力的机器可验证基线。
## Requirements
### Requirement: 16组PARTID cache设置

每个L3/SLC MSC MUST 为PARTID 0到15提供独立设置和监控项。

#### Scenario: 检查空闲PARTID

- **WHEN** 某PARTID在周期内没有请求
- **THEN** 其监控行仍然存在且活动计数为零

### Requirement: L3分配控制

当前L3模型 MUST 使用CPBM作为eligible-way mask，使用CMAX作为PARTID可占物理L3的
最大比例，使用CMIN保护已由需求填充的最小比例。

#### Scenario: 限制比例增长

- **WHEN** PARTID达到有效CMAX
- **THEN** 其采样set聚合owner数量不能继续增长

#### Scenario: 保护比例下限

- **WHEN** victim PARTID处于或低于有效CMIN采样目标
- **THEN** 其他PARTID不能驱逐该victim

### Requirement: 每个monitor group采样1个set

L3 MUST 在每个monitor group中维护可轮转读取的sampled-owner counter bank，并把采样访问和
占用按monitor group比例估算。采样offset MUST 支持固定offset 0和按本地监控周期轮转两种模式。

#### Scenario: 访问固定采样set

- **WHEN** `sampling_mode=fixed_first`且`set_index modulo monitor_group_sets == 0`
- **THEN** 更新采样访问计数
- **AND** fill/replacement MUST 更新offset 0的sampled-owner counter bank

#### Scenario: 访问轮转采样set

- **WHEN** `sampling_mode=rotating`且`set_index modulo monitor_group_sets == sampling_offset`
- **THEN** 更新当前offset对应的采样访问计数
- **AND** fill/replacement MUST 更新`set_index modulo monitor_group_sets`对应的sampled-owner counter bank

#### Scenario: 访问非采样set

- **WHEN** 访问组内其他set
- **THEN** 当前窗口不为该访问更新采样访问计数

### Requirement: 控制关闭时仍监控

`no_control` MUST 保留16组监控，同时报告不受限的有效cache设置。

#### Scenario: 不启用MPAM强制

- **WHEN** policy为`no_control`
- **THEN** CPBM、CMIN和CMAX不限制分配，但监控行保留

### Requirement: PMG分组cache监控

L3 MUST 按`(PARTID, PMG)`归因采样流量和采样way owner，控制仍按PARTID。

#### Scenario: 采样line分配

- **WHEN** PARTID P、PMG G的miss分配采样way
- **THEN** 该way记录P和G用于占用归因

#### Scenario: 报告分组占用

- **WHEN** 捕获cache周期快照
- **THEN** 每个活动监控组报告采样请求、估算带宽、占用和利用率

### Requirement: 独立L3控制开关

每个PARTID MUST 独立开关CPBM、CMIN和CMAX，同时保留配置值。

#### Scenario: 仅关闭CPBM

- **WHEN** CPBM关闭而CMAX开启
- **THEN** 所有物理way可用，CMAX仍限制分配

#### Scenario: 仅关闭CMIN

- **WHEN** CMIN关闭
- **THEN** 不执行最小保护，其他控制保持

#### Scenario: 仅关闭CMAX

- **WHEN** CMAX关闭
- **THEN** 有效最大值由有效CPBM可达way决定

### Requirement: 有界L3请求队列

每个L3/SLC MSC MUST 通过可配置FIFO接收请求，并限制并发lookup数量。

#### Scenario: 队列有空间

- **WHEN** 请求到达且有entry
- **THEN** 请求入队、等待lookup并记录queue delay

#### Scenario: 队列已满

- **WHEN** 请求到达且队列满
- **THEN** 请求稍后重试并累计L3 admission backpressure

### Requirement: 可配置L3 CBusy响应

L3 MUST 支持可配置的CBusy响应动作。开启时，L3在fill返回路径用MSHR owner本地上下文
把返回旁带中的CBusy level归因到PARTID，并仅限制同PARTID后续新miss的MSHR分配。

#### Scenario: 返回旁带归因PARTID

- **WHEN** MC返回的DAT/RSP携带CBusy level并完成某个L3 MSHR
- **THEN** L3 MUST 使用该MSHR owner request的PARTID更新本地CBusy状态
- **AND** MUST NOT 要求L3保存MC issue time作为控制输入

#### Scenario: 新miss MSHR被限制

- **WHEN** L3 CBusy响应开启、PARTID P的level大于0且P的当前MSHR数量达到该level cap
- **THEN** P的后续新miss MUST 等待MSHR准入
- **AND** hit、fill、response和已分配MSHR MUST NOT 被CBusy门控

#### Scenario: L3响应关闭

- **WHEN** L3 CBusy响应开关关闭
- **THEN** L3 MUST 忽略返回CBusy动作并按普通MSHR容量准入新miss

### Requirement: L3队列监控

L3 MUST 报告queue depth、lookup parallelism、平均/峰值占用、active lookup、
queue delay和queue-full事件。

#### Scenario: 观察L3压力

- **WHEN** offered lookup并发超过可用lookup slot
- **THEN** queue occupancy和queue delay变为非零

### Requirement: CMIN感知的CMAX以下增长

低于CMAX的PARTID可以替换eligible的LRU victim，但victim owner MUST 保持在CMIN以上。

#### Scenario: Aggressor竞争受保护owner

- **WHEN** aggressor低于CMAX且victim owner处于CMIN
- **THEN** 跳过该victim并寻找其他合法victim

### Requirement: 比例控制校验

配置 MUST 满足`0 <= CMIN <= CMAX <= 100`，启用CMIN总和不能超过100%，
CMIN不能超过CPBM可达比例。

#### Scenario: CMIN过量

- **WHEN** 同一L3启用CMIN总和超过100%
- **THEN** 配置校验失败

#### Scenario: CMAX总和超过100%

- **WHEN** 多个CMAX总和超过100%
- **THEN** 配置仍有效，因为CMAX是独立上限

### Requirement: 控制与监控共享真实Line状态

CPBM、CMIN、CMAX、实际占用和可配1/8抽样监控 MUST 基于同一组真实L3 line，不得维护独立
owner影子作为控制事实。

#### Scenario: 非抽样Set分配

- **WHEN** PARTID在非抽样set完成fill
- **THEN** actual occupancy增加而本次sampled occupancy可以不增加

#### Scenario: 固定抽样Set分配

- **WHEN** `sampling_mode=fixed_first`且PARTID在每个抽样组offset 0的set完成fill
- **THEN** actual owner来自line owner字段
- **AND** sampled owner来自offset 0对应的sampled-owner counter bank

#### Scenario: 轮转抽样Set分配

- **WHEN** `sampling_mode=rotating`
- **THEN** L3 MUST 每隔`sampling_rotation_period_monitor_cycles`个本地监控周期把组内采样offset加1并对`monitor_group_sets`取模
- **AND** sampled owner MUST 读取当前采样offset对应的sampled-owner counter bank

### Requirement: L3 sampled-owner counter bank

L3 sampled-owner监控 MUST 使用按offset划分的owner计数器近似硬件监控，而不是在监控边界瞬时扫描所有tag/way owner。
当line owner在fill或replacement时变化，L3 MUST 更新：

```text
offset = set_index mod monitor_group_sets
owner_count[offset][PARTID]
owner_count_by_pmg[offset][PARTID, PMG]
```

#### Scenario: Fill到空way

- **WHEN** PARTID P、PMG G在set S填入空way
- **THEN** `owner_count[S mod monitor_group_sets][P]` MUST 加1
- **AND** `(P, G)`监控组counter MUST 加1

#### Scenario: Replacement替换victim

- **WHEN** PARTID P、PMG G替换原owner V、PMG H的valid line
- **THEN** victim对应offset counter MUST 减1
- **AND** 新owner对应offset counter MUST 加1
- **AND** counter不得降到负值

#### Scenario: Monitor boundary读取

- **WHEN** L3运行到本地监控周期边界
- **THEN** raw sampled owner MUST 从当前offset的counter bank读取
- **AND** 该读取不要求在同一边界扫描所有sampled set/way

### Requirement: L3本地周期MPAM监控

L3 MUST 每个可配本地监控周期发布所有PARTID的raw抽样owner、control sampled owner和抽样访问带宽。
L3 occupancy是缓存状态的抽样绝对值，不得把CMIN/CMAX输入建模成带宽式递归滤波值。

#### Scenario: 256拍发布

- **WHEN** L3运行到一个监控周期边界
- **THEN** raw读取当前采样offset对应的sampled-owner counter bank
- **AND** control sampled owner MUST 保存为本边界发布的raw sampled owner
- **AND** sampled access bandwidth MAY 按`history_weight + current_weight = 1`的权重滤波

### Requirement: CMIN和CMAX只读发布后的抽样占用

CMIN/CMAX MUST 使用本地监控边界发布并保存的control sampled-owner值执行保护和增长限制。

#### Scenario: 当前物理状态变化

- **WHEN** 当前周期物理owner变化但尚未到监控边界
- **THEN** CMIN/CMAX决策输入保持上一控制窗口保存值

#### Scenario: 边界后进入下一控制窗口

- **WHEN** 监控边界T基于刚关闭窗口raw owner计算出新的control sampled-owner
- **THEN** 该值 MAY 立即用于UI、导出和证据
- **AND** 后续控制窗口中的CMIN/CMAX动作才可以读取该值
- **AND** 边界T之前已经完成的victim选择不得回溯使用该值

### Requirement: L3控制事件证据

L3 CMIN/CMAX内部控制状态切换 MUST 复用常规`ControlEvent`通路。

#### Scenario: CMIN CMAX状态变化

- **WHEN** L3本地监控边界锁存的control input改变CMIN保护或CMAX限制状态
- **THEN** MUST 导出`limit_state_changed`控制事件
- **AND** 事件 MUST 引用`control_input` monitor sample
- **AND** 事件 SHOULD 包含control sampled-owner、quota、raw sampled owner、sampling mode和sampling offset证据

### Requirement: 三平面误差证据

监控 MUST 同时导出physical actual、raw sampled-owner、published/control sampled-owner及其差值。

#### Scenario: 地址交织造成抽样误差

- **WHEN** 非抽样set的owner分布与抽样set不同
- **THEN** UI和导出明确显示raw/published sampled与physical之间的误差
