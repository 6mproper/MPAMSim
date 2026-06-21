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

### Requirement: 每8个set采样1个

L3 MUST 采样每8个set中的第一个set，并把采样访问和占用按8倍估算。

#### Scenario: 访问采样set

- **WHEN** `set_index modulo 8 == 0`
- **THEN** 更新采样way owner和流量计数

#### Scenario: 访问非采样set

- **WHEN** 访问组内其他set
- **THEN** 当前实现不为该访问更新采样tag/way状态

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
