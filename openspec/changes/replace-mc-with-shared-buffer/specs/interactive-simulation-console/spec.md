## ADDED Requirements

### Requirement: MC周期控制配置和证据

控制台 MUST 配置MC clock、256拍周期、filter weights、滞回和service deficit，并显示
raw/latest filtered/control input BW、UNDER/OVER/HARD状态、candidate、grant和QoS饱和。

#### Scenario: 查看Hard BMAX说明

- **WHEN** 用户指向hard limit或MC monitor配置
- **THEN** 说明上一周期输入、过冲、整周期门控、滞回释放和buffer增长
