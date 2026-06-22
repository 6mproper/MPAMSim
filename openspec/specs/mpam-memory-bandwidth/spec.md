# mpam-memory-bandwidth 规格

## Purpose

定义当前已实现的每MC、每PARTID带宽设置、token限制、3-bit QoS调度、
四档CBusy和监控行为，作为当前memory-controller MSC能力的机器可验证基线。
## Requirements
### Requirement: 16组PARTID memory设置

每个MC MSC MUST 为PARTID 0到15提供独立带宽设置、token状态、3-bit MC QoS和监控项。

#### Scenario: 配置MC QoS

- **WHEN** 软件配置PARTID MC QoS
- **THEN** 取值 MUST 在`[0, 7]`且仅用于MC仲裁

### Requirement: BMAX hard limit

当前MC模型 MUST 用每PARTID token bucket实现hard BMAX，token不足时阻止dispatch。

#### Scenario: 超过hard limit

- **WHEN** `hardlimit`请求缺少BMAX token
- **THEN** dispatch等待、throttle delay增加并记录hard-block事件

### Requirement: BMAX soft limit

soft-limit请求 MUST 保持eligible，仅在超过BMAX且存在竞争时降低有效MC QoS。

#### Scenario: 无竞争soft limit

- **WHEN** PARTID超过BMAX但没有其他eligible contender
- **THEN** 不降低QoS，服务保持work-conserving

#### Scenario: 有竞争soft limit

- **WHEN** PARTID超过BMAX且存在其他eligible请求
- **THEN** 有效QoS按配置值降低并钳位

### Requirement: BMIN近似

当前MC scheduler MUST 对被BMIN credit覆盖的candidate提升有效QoS。

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

当前模型 MUST 配置token window、aging quantum、aging cap、BMIN promotion和
soft-limit demotion。

#### Scenario: 修改BMIN提升

- **WHEN** 增大BMIN promotion
- **THEN** under-BMIN candidate使用新提升值

### Requirement: 控制算法证据

监控 MUST 提供BMIN credit、soft-limit、hard-block、throttle和QoS证据。

#### Scenario: 检查受控周期

- **WHEN** BMIN或BMAX影响选择
- **THEN** 输出 MUST 标识配置常量、base/effective QoS和受影响请求

### Requirement: 3-bit QoS仲裁

当前MC scheduler MUST 选择最高有效QoS，相同QoS选择最老请求。

#### Scenario: QoS钳位

- **WHEN** aging、BMIN或soft demotion改变QoS
- **THEN** 有效QoS保持在0到7

#### Scenario: Hard limit阻塞高QoS

- **WHEN** QoS 7请求缺少hard BMAX token
- **THEN** token恢复前排除该请求

### Requirement: 上一滤波周期驱动BMIN和BMAX

周期k的BMIN/BMAX MUST 只读取周期k-1发布的滤波带宽，不得读取当前瞬时服务字节。

#### Scenario: Hard BMAX过冲

- **WHEN** 当前周期服务使raw带宽超过BMAX
- **THEN** 请求可在本周期继续服务，hard block从下一周期生效

### Requirement: Work-Conserving Soft控制

BMIN提升和soft BMAX降低 MUST 只在至少两个不同PARTID有ready candidate时影响QoS。

#### Scenario: Soft BMAX无竞争

- **WHEN** 一个OVER_BMAX PARTID是唯一ready PARTID
- **THEN** 请求保持eligible且不因soft控制降低可用带宽

### Requirement: Hard BMAX周期门控

hard OVER_BMAX状态 MUST 在整个控制周期内阻止该PARTID所有entry服务，直到滤波值达到滞回释放阈值。

#### Scenario: Hard Block

- **WHEN** 上一发布filtered BW使hard OVER_BMAX有效
- **THEN** 该PARTID entry保留在buffer且不参与candidate选择
