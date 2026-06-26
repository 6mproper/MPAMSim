# Change: 将resctrl-like配置并入MPAM页签

## Why

resctrl-like配置本质上是MPAM配置的一个软件入口，会映射到内部PARTID/PMG和现有MPAM控制。
独立页签会让用户误以为它是与MPAM并列的控制面。

## What Changes

- 移除顶部独立`resctrl`页签。
- 将resctrl-like软件资源组配置区显示在MPAM页签内。
- 保留原有resctrl DOM id和数据收集逻辑，避免引入新的配置通路。

## Impact

- UI导航更紧凑，resctrl和直接MPAM配置的关系更清楚。
- 不改变后端配置生成、resctrl映射、仿真模型或结果数据结构。
