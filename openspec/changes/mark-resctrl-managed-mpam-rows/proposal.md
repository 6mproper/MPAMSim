## 背景

resctrl-like模式开启后，软件组会在提交前覆盖对应PARTID的部分MPAM页签配置。当前UI没有在MPAM表中提示这些行被resctrl接管，用户容易误以为两边配置会同时生效。

## 目标

- 当resctrl-like模式开启时，在MPAM页签对应PARTID行显示“由resctrl接管”。
- 标记随resctrl开关、CTRL_MON group启用状态和PARTID修改实时刷新。
- 不改变配置转换和仿真模型。

## 非目标

- 不禁用MPAM字段。
- 不新增新的配置优先级。
- 不修改resctrl到MPAM的映射规则。
