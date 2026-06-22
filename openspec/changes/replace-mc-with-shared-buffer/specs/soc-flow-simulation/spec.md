## ADDED Requirements

### Requirement: MC共享Buffer全候选

MC MUST 让共享buffer中所有valid、ready且未被hard BMAX或ordering阻塞的entry参与QoS比较。

#### Scenario: 高QoS位于非队首Slot

- **WHEN** 一个高QoS ready entry位于共享buffer后部
- **THEN** 它仍参与本次最高QoS选择

### Requirement: 同Line最小顺序

MC MUST 允许同line read/read重排，并阻止任何包含write的较新同line entry越过较老entry。

#### Scenario: Write后Read

- **WHEN** 较老write和较新read访问同一line
- **THEN** 较新read在write离开buffer前不可调度

### Requirement: Rotating Slot仲裁

同最高QoS候选 MUST 从上次grant slot之后旋转扫描选择，不使用enqueue时间作为默认比较。

#### Scenario: 相同QoS持续竞争

- **WHEN** 多个slot持续保持相同最高QoS
- **THEN** grant位置按slot轮转且确定性前进
