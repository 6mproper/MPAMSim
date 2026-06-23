## ADDED Requirements

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

- **WHEN** 上一监控边界锁存的control bandwidth使hard OVER_BMAX有效
- **THEN** 该PARTID entry保留在buffer且不参与candidate选择
