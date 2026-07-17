## ADDED Requirements

### Requirement: 控制总览L3和MC主图支持多PARTID对比

控制台 MUST 允许用户为控制总览的 L3 与 MC 主图选择一个或多个 PARTID 并在同一张图中叠加显示。
该选择 MUST 独立于当前单个 PARTID 状态卡选择，也 MUST 独立于高级资源视图的可见 PARTID 筛选。

#### Scenario: 多选PARTID同图显示

- **WHEN** 用户在控制总览中勾选多个同图对比 PARTID
- **THEN** L3 主图 MUST 为每个所选 PARTID 显示已开启图层对应的目标带、control input、actual、published monitor或raw曲线
- **AND** MC 主图 MUST 为每个所选 PARTID 显示已开启图层对应的目标带、control input、actual raw、可选actual MA、latest filtered或raw曲线
- **AND** 控制事件标记 MUST 覆盖所选 PARTID 的控制事件时间

#### Scenario: 图例可区分颜色和线型

- **WHEN** L3或MC主图显示多个 PARTID
- **THEN** 图例 MUST 用颜色标识 PARTID
- **AND** MUST 用线型、点型或填充标识目标带、control input、actual、published/raw和控制事件

#### Scenario: 状态卡保持单PARTID语义

- **WHEN** 用户只改变同图对比 PARTID
- **THEN** CPU OSTD、L3 MSC和MC MSC状态卡 MUST 仍显示当前 PARTID 选择的状态
- **AND** 不得把多 PARTID 状态聚合到单个状态卡中
