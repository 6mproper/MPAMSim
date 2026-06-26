## 背景

MC带宽监控使用短窗口raw bandwidth和历史filtered bandwidth计算控制输入。当前默认
`history_weight=0.75`、`current_weight=0.25`对短仿真窗口响应较快，但也会让带宽监控更敏感于
burst、量化和BMAX/CBusy动作造成的周期性波动。

## 目标

- 将MC bandwidth filtered monitor默认权重调整为`history_weight=0.95`、`current_weight=0.05`。
- 保持L3 sampled access bandwidth默认权重不变。
- 保持用户界面可配置，且继续要求两个权重之和等于1。

## 非目标

- 不改变MC BMIN/BMAX公式和控制时序。
- 不改变L3 occupancy sampled-owner语义。
- 不改变已有配置文件中显式写入的权重。
