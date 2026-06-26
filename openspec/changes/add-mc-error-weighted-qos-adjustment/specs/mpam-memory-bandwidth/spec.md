## MODIFIED Requirements

### Requirement: BMAX soft limit

soft-limit请求 MUST 保持eligible，仅在超过BMAX且存在竞争时降低有效MC QoS。
MC MUST 支持两种可配置QoS调整模式：

- `fixed_step`：soft降档等于`softlimit_qos_demote`。
- `error_weighted`：soft降档由已发布并锁存的`control_bandwidth`相对BMAX目标的超限误差计算。

`error_weighted`模式不得读取actual/debug带宽或当前周期未发布服务量。

#### Scenario: 无竞争soft limit

- **WHEN** PARTID超过BMAX但没有其他eligible contender
- **THEN** 不降低QoS，服务保持work-conserving

#### Scenario: 有竞争soft limit

- **WHEN** PARTID超过BMAX且存在其他eligible请求
- **THEN** 有效QoS按当前QoS调整模式降低并钳位

#### Scenario: 误差加权soft limit

- **GIVEN** MC QoS调整模式为`error_weighted`
- **AND** `control_bandwidth`超过BMAX目标且超过deadband
- **WHEN** MC执行候选选择
- **THEN** soft降档 MUST 按`(control_bandwidth - BMAX) / BMAX`、BMAX error weight、quantization和max delta计算
- **AND** 该delta MUST 作为本次Transaction仲裁证据保存

### Requirement: BMIN近似

当前MC scheduler MUST 在存在跨PARTID竞争且PARTID处于UNDER_BMIN状态时提升有效QoS。
MC MUST 支持两种可配置QoS调整模式：

- `fixed_step`：BMIN升档等于`bmin_qos_promote`。
- `error_weighted`：BMIN升档由BMIN目标与已发布并锁存的`control_bandwidth`的欠量误差计算。

#### Scenario: 低于BMIN竞争

- **WHEN** 请求被BMIN状态覆盖
- **THEN** 有效QoS按当前QoS调整模式提升并钳位

#### Scenario: 误差加权BMIN

- **GIVEN** MC QoS调整模式为`error_weighted`
- **AND** `control_bandwidth`低于BMIN目标且超过deadband
- **WHEN** MC执行候选选择
- **THEN** BMIN升档 MUST 按`(BMIN - control_bandwidth) / BMIN`、BMIN error weight、quantization和max delta计算
- **AND** 该delta MUST 作为本次Transaction仲裁证据保存

### Requirement: 可配置MC调度常量

当前模型 MUST 配置monitor周期、history/current滤波权重、滞回、aging quantum、aging cap、
QoS调整模式、固定BMIN promotion、固定soft-limit demotion，以及error-weighted模式的
BMIN/BMAX error weight、deadband、max delta和quantization。

#### Scenario: 切换QoS调整模式

- **WHEN** 用户选择`fixed_step`
- **THEN** MC MUST 使用固定`bmin_qos_promote`和`softlimit_qos_demote`
- **WHEN** 用户选择`error_weighted`
- **THEN** MC MUST 使用误差加权参数计算delta

### Requirement: 3-bit QoS仲裁

当前MC scheduler MUST 先计算raw 3-bit effective QoS：
`raw_effective_qos = clamp(base_qos + bmin_delta - softlimit_delta + service_deficit, 0, 7)`。
其中`bmin_delta`和`softlimit_delta`由当前QoS调整模式决定。
MC MUST 支持可配置的8级到4级映射开关。关闭时，最终仲裁QoS MUST 等于raw 3-bit effective QoS。
开启时，最终仲裁QoS MUST 按`0,1,2,3,4,5,6,7 -> 0,1,1,1,2,2,2,3`映射。
MC MUST 使用最终仲裁QoS选择最高档，相同最终QoS使用rotating buffer-slot scan。

#### Scenario: QoS钳位

- **WHEN** aging、BMIN或soft demotion改变QoS
- **THEN** 有效QoS保持在0到7

#### Scenario: QoS证据

- **WHEN** MC导出监控快照
- **THEN** 每个PARTID和监控组 MUST 提供raw effective QoS统计、最终effective QoS统计、QoS调整模式、delta统计、映射开关状态和映射事件计数
