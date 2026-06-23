# mpam-memory-bandwidth 规格

## Purpose

定义当前已实现的每MC、每PARTID带宽设置、共享buffer、上一滤波周期控制、
3-bit QoS调度、四档CBusy返回旁带和监控行为，作为当前memory-controller MSC能力的机器可验证基线。
## Requirements
### Requirement: 16组PARTID memory设置

每个MC MSC MUST 为PARTID 0到15提供独立带宽设置、3-bit MC QoS、CBusy状态和监控项。

#### Scenario: 配置MC QoS

- **WHEN** 软件配置PARTID MC QoS
- **THEN** 取值 MUST 在`[0, 7]`且仅用于MC仲裁

### Requirement: 共享MC请求buffer

当前MC模型 MUST 使用一个固定深度共享request buffer。除hard BMAX或同line最小顺序阻塞外，
所有valid entry都参与QoS候选比较。

#### Scenario: 全深度候选

- **WHEN** buffer中多个slot有ready entry
- **THEN** scheduler MUST 比较全部ready entry而不是只看每PARTID队首

#### Scenario: 同line最小顺序

- **WHEN** 两个请求访问同一cache line且任一请求为write
- **THEN** 较新请求 MUST 等待较老请求离开buffer

### Requirement: BMAX hard limit

当前MC模型 MUST 根据上一发布filtered bandwidth形成hard OVER_BMAX状态，并在整个监控周期内
阻止该PARTID entry参与dispatch。

#### Scenario: 超过hard limit

- **WHEN** `hardlimit`的上一发布filtered bandwidth超过BMAX
- **THEN** 该PARTID entry保留在buffer且不参与candidate选择，并记录hard-block和throttle证据

### Requirement: BMAX soft limit

soft-limit请求 MUST 保持eligible，仅在超过BMAX且存在竞争时降低有效MC QoS。

#### Scenario: 无竞争soft limit

- **WHEN** PARTID超过BMAX但没有其他eligible contender
- **THEN** 不降低QoS，服务保持work-conserving

#### Scenario: 有竞争soft limit

- **WHEN** PARTID超过BMAX且存在其他eligible请求
- **THEN** 有效QoS按配置值降低并钳位

### Requirement: BMIN近似

当前MC scheduler MUST 在存在跨PARTID竞争且PARTID处于UNDER_BMIN状态时提升有效QoS。

#### Scenario: 低于BMIN竞争

- **WHEN** 请求被BMIN credit覆盖
- **THEN** 有效QoS按配置级数提升并钳位

### Requirement: 带宽监控

MC MUST 按PARTID报告带宽、BMIN/BMAX、mode、base/effective QoS、queue/service/
throttle delay、soft-limit请求和hard-block事件。

#### Scenario: 多MC聚合

- **WHEN** UI聚合多个MC快照
- **THEN** 带宽和配置limit MUST 标明为跨实例求和

### Requirement: PMG分组带宽监控

MC MUST 按`(PARTID, PMG)`归因已服务请求和字节，控制仍按PARTID。

#### Scenario: 服务监控组请求

- **WHEN** MC dispatch PARTID P、PMG G的请求
- **THEN** 对应组记录请求、字节、延迟和limit事件

### Requirement: 独立MC控制开关

每个PARTID MUST 独立开关BMIN、BMAX、MC QoS和CBusy。

#### Scenario: 关闭BMAX

- **WHEN** BMAX关闭
- **THEN** 不执行hard token阻塞或soft demotion，其他控制可保持

#### Scenario: 关闭MC QoS

- **WHEN** MC QoS关闭
- **THEN** 保留配置值，但base arbitration QoS为0

### Requirement: 四档PARTID CBusy

每个MC MUST 为每个启用CBusy的PARTID独立生成Level 0到3。

#### Scenario: 断言压力

- **WHEN** queue、hard-block或竞争带宽超过阈值
- **THEN** 提升到最高匹配等级

#### Scenario: 释放压力

- **WHEN** detector输入降低
- **THEN** 满足hold后每次下降一级

#### Scenario: CBusy关闭

- **WHEN** PARTID关闭CBusy
- **THEN** 始终报告和发送Level 0

### Requirement: 可配置MC调度常量

当前模型 MUST 配置monitor周期、history/current滤波权重、滞回、aging quantum、
aging cap、BMIN promotion和soft-limit demotion。

#### Scenario: 修改BMIN提升

- **WHEN** 增大BMIN promotion
- **THEN** under-BMIN candidate使用新提升值

### Requirement: 控制算法证据

监控 MUST 提供BMIN credit、soft-limit、hard-block、throttle和QoS证据。

#### Scenario: 检查受控周期

- **WHEN** BMIN或BMAX影响选择
- **THEN** 输出 MUST 标识配置常量、base/effective QoS和受影响请求

### Requirement: 3-bit QoS仲裁

当前MC scheduler MUST 选择最高有效QoS，相同QoS使用rotating buffer-slot scan。

#### Scenario: QoS钳位

- **WHEN** aging、BMIN或soft demotion改变QoS
- **THEN** 有效QoS保持在0到7

#### Scenario: 相同QoS

- **WHEN** 多个ready entry具有相同最高effective QoS
- **THEN** 从上次grant slot之后旋转扫描选择下一个slot

#### Scenario: Hard limit阻塞高QoS

- **WHEN** QoS 7请求处于hard OVER_BMAX状态
- **THEN** hard状态释放前排除该请求

### Requirement: 上一滤波周期驱动BMIN和BMAX

周期k的BMIN/BMAX MUST 只读取本地监控边界锁存的周期k-1发布滤波带宽，不得读取当前瞬时服务字节。

#### Scenario: Hard BMAX过冲

- **WHEN** 当前周期服务使raw带宽超过BMAX
- **THEN** 请求可在本周期继续服务，hard block从下一周期生效

#### Scenario: BMAX发布不立即控制

- **WHEN** 当前窗口服务字节使本边界发布的filtered bandwidth超过BMAX
- **THEN** 该PARTID在本边界之后的同timestamp调度 MUST NOT 因这个刚发布值立即hard block或soft demote
- **AND** hard/soft控制最早在下一次本地监控边界锁存该filtered值后生效

#### Scenario: BMAX释放延迟

- **WHEN** hard block后的窗口不再服务该PARTID并发布低于释放阈值的filtered bandwidth
- **THEN** hard block MUST 在下一次本地监控边界锁存该低filtered值后释放
- **AND** 释放延迟和过冲 MUST 记录为可观察控制结果，不得中止仿真

#### Scenario: CBusy带宽输入

- **WHEN** CBusy detector使用带宽比例判断等级
- **THEN** 带宽比例 MUST 基于锁存的`control_bandwidth / BMAX`
- **AND** queue比例仍 MAY 基于当前授权buffer状态

### Requirement: MC控制事件证据

MC BMIN/BMAX内部控制状态切换 MUST 复用常规`ControlEvent`通路。

#### Scenario: BMIN BMAX状态变化

- **WHEN** MC本地监控边界锁存的control bandwidth改变UNDER_BMIN、OVER_BMAX或hard block状态
- **THEN** MUST 导出`limit_state_changed`控制事件
- **AND** 事件 MUST 引用`control_input` monitor sample
- **AND** 事件 SHOULD 包含control bandwidth、latest filtered、阈值、滞回和limit mode证据

### Requirement: Work-Conserving Soft控制

BMIN提升和soft BMAX降低 MUST 只在至少两个不同PARTID有ready candidate时影响QoS。

#### Scenario: Soft BMAX无竞争

- **WHEN** 一个OVER_BMAX PARTID是唯一ready PARTID
- **THEN** 请求保持eligible且不因soft控制降低可用带宽

### Requirement: Hard BMAX周期门控

hard OVER_BMAX状态 MUST 在整个控制周期内阻止该PARTID所有entry服务，直到滤波值达到滞回释放阈值。

#### Scenario: Hard Block

- **WHEN** 上一监控边界锁存的control bandwidth使hard OVER_BMAX有效
- **THEN** 该PARTID entry保留在buffer且不参与candidate选择

### Requirement: CBusy返回旁带

MC MUST 每`cbusy_sample_ns`更新每PARTID CBusy level，但RN只能从自己收到的终端RSP或最后DAT
旁带学习`(MC, PARTID)`状态。

#### Scenario: 返回携带CBusy

- **WHEN** MC服务完成一个请求
- **THEN** transaction MUST 采样当前`(MC, PARTID)` CBusy level和OSTD cap并随返回路径携带

#### Scenario: 仅更新返回目的RN

- **WHEN** 返回到达requester R
- **THEN** 只有R的匹配`(MC, PARTID)`反馈表更新，同PARTID其他requester MUST 不被广播更新

#### Scenario: 无返回保持陈旧

- **WHEN** MC本地CBusy level变化但某RN没有收到该MC/PARTID返回
- **THEN** 该RN继续使用旧反馈状态
