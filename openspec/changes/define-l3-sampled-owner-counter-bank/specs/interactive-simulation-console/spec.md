## MODIFIED Requirements

### Requirement: 控制总览区分control input和latest filtered

控制总览 MUST 将控制器实际读取的锁存值显示为control input。L3 occupancy MUST 把raw、
published和control input标注为sampled-owner语义；MC bandwidth等速率量
MAY 继续使用latest filtered bandwidth。

#### Scenario: L3和MC主图

- **WHEN** 用户查看控制总览
- **THEN** L3主图图例 MUST 避免把occupancy主线标成latest filtered
- **AND** MC主图 MAY 继续显示latest filtered bandwidth图层
- **AND** actual、raw和控制事件仍按显示层开关控制

#### Scenario: 文案区分

- **WHEN** UI解释L3 raw、published、control input或actual
- **THEN** L3 raw MUST 说明来自当前采样offset counter bank
- **AND** published MUST 说明为监控边界对外发布的sampled-owner快照
- **AND** control input MUST 表示控制器读取的锁存sampled-owner
