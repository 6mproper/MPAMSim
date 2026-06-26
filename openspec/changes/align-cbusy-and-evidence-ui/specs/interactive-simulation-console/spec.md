## MODIFIED Requirements

### Requirement: 控制总览区分control input和latest filtered

控制总览 MUST 将控制器实际读取的锁存值显示为control input。L3 occupancy MUST 把最新发布值显示为
published sampled-owner；MC bandwidth MAY 继续使用latest filtered bandwidth。控制总览默认 MUST
聚焦目标带、control input、actual和控制事件；raw sampled-owner与published sampled-owner MUST
保留为可选高级证据层。

#### Scenario: L3和MC主图默认图层

- **WHEN** 用户打开控制总览
- **THEN** 主图默认 MUST 显示目标带、control input、actual和控制事件
- **AND** raw sampled-owner、published sampled-owner和MC raw/latest filtered MUST 可通过图层开关显示
- **AND** 这些开关 MUST 只影响前端显示，不重新仿真

#### Scenario: 文案区分

- **WHEN** UI解释raw、published、control input或actual
- **THEN** L3 occupancy文案 MUST 说明raw sampled-owner来自当前采样offset counter bank
- **AND** published sampled-owner MUST 说明为监控边界对外发布的sampled-owner快照
- **AND** control input MUST 表示控制器读取的锁存监控值
- **AND** actual MUST 标注为验证用观测值，不得描述为控制输入
