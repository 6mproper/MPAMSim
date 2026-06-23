## ADDED Requirements

### Requirement: Workload地址基址

常规workload MUST 支持可配置`address_base_bytes`，并在生成地址后统一加到事务地址上。

#### Scenario: 分离两个顺序流

- **WHEN** 两个workload使用相同`address_pattern=sequential`但配置不同`address_base_bytes`
- **THEN** 两个workload MUST 访问不同cache line窗口
- **AND** 不得为了P1关闭真实L3同line merge机制

### Requirement: P1预设可打出独立PARTID归因

控制效果预设 MUST 避免用完全重叠的同line地址流掩盖多PARTID的MC或L3归因。

#### Scenario: MC竞争预设

- **WHEN** 用户应用`MC BMIN / QoS 竞争`预设并运行仿真
- **THEN** `PARTID 0`和`PARTID 1` SHOULD 都能产生MC请求和带宽归因
- **AND** 若任一PARTID被同line merge掩盖，预设不满足P1可观察性目标

## MODIFIED Requirements

### Requirement: 阶段命名与PARTID命名消歧

规格、OpenSpec change、测试说明和UI文案 MUST 明确区分阶段命名与MPAM PARTID命名。

#### Scenario: 描述MPAM标识

- **WHEN** 文档、测试或UI文案描述MPAM PARTID编号
- **THEN** MUST 写成`PARTID 0`、`PARTID 1`、`PARTID 2`或`PARTID N`
- **AND** MUST NOT 使用`P0`、`P1`、`P2`缩写PARTID
