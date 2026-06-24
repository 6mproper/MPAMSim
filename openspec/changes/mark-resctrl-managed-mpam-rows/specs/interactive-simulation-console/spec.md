## ADDED Requirements

### Requirement: MPAM行显示resctrl接管状态

当resctrl-like模式启用时，MPAM页签 MUST 在被启用CTRL_MON group映射到的PARTID行显示“由resctrl接管”状态，提醒用户该行部分字段会由resctrl软件组转换结果覆盖。

#### Scenario: resctrl开启后显示接管标记

- **WHEN** 用户启用resctrl-like模式
- **THEN** MPAM页签中所有被启用CTRL_MON group映射的PARTID行 MUST 显示“由resctrl接管”
- **AND** 标记 SHOULD 说明对应软件组名称

#### Scenario: resctrl关闭后隐藏接管标记

- **WHEN** 用户关闭resctrl-like模式
- **THEN** MPAM页签中 MUST 不显示resctrl接管标记
