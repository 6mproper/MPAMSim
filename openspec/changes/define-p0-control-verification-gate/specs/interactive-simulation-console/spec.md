## ADDED Requirements

### Requirement: P0控制验证展示

控制台 MUST 将P0验证展示为机制生效证据，而不是目标达成证明。

#### Scenario: 显示失败检查

- **WHEN** 控制验证套件中某个机制检查未通过
- **THEN** 控制台 MUST 显示该check失败和证据
- **AND** 不得把目标未达、过冲或饱和等CONTROL_OUTCOME显示为仿真失败

### Requirement: P0因果链复用常规界面

控制台 MUST 使用现有控制总览、因果链和高级证据通路展示P0证据。

#### Scenario: 查看P0证据

- **WHEN** 用户查看L3或MC/CPU控制效果
- **THEN** 控制台 MUST 通过目标带、filtered、raw、actual和控制事件展示证据
- **AND** 不得新增只服务P0的独立结果页面或专用数据通道
