## MODIFIED Requirements

### Requirement: 证据工作区统一视图

Web控制台 MUST 在结果面板顶部提供PARTID多选器，所选PARTID颜色映射到所有证据图表。
控制效果视图 MUST 在共享时间游标下展示L3占用、MC带宽、CBusy/OSTD和P99四张自适应图表，
并包含底部控制事件时间线。

#### Scenario: PARTID单色联动

- **WHEN** 用户选择PARTID 3
- **THEN** 所有图表中PARTID 3的数据使用同一颜色，事件时间线中PARTID 3事件使用相同颜色

#### Scenario: 事件时间线标记

- **WHEN** 仿真完成后打开控制效果视图
- **THEN** 事件时间线按时间轴显示所有setting_applied、cbusy_update和feedback_delivered事件
