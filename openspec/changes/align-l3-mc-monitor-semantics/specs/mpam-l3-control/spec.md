## MODIFIED Requirements

### Requirement: L3近似Monitor Group

L3 MPAM occupancy监控 MUST 基于sampled-owner绝对状态，而不是默认滑动平均值。

#### Scenario: Fixed first sampling

- **WHEN** `sampling_mode=fixed_first`
- **THEN** 每个8-set monitor group MUST 固定采样组内offset 0的set
- **AND** sampled occupancy MUST 由该采样set的way owner PARTID统计得到

#### Scenario: Rotating sampling

- **WHEN** `sampling_mode=rotating`
- **THEN** 每隔`sampling_rotation_period_monitor_cycles`个L3监控周期 MUST 将组内采样offset加1并对`monitor_group_sets`取模
- **AND** sampled occupancy MUST 由当前offset对应set的way owner PARTID统计得到

### Requirement: CMIN CMAX读取占用控制输入

CMIN/CMAX MUST 使用L3本地监控边界锁存的sampled-owner occupancy绝对值执行保护和增长限制。

#### Scenario: 下一周期控制输入

- **WHEN** L3监控边界基于当前采样offset得到sampled-owner count
- **THEN** 该sampled-owner count MUST 被锁存为新控制周期的control input
- **AND** actual occupancy MUST NOT 作为CMIN/CMAX控制输入
