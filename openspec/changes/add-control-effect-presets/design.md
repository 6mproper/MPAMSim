## 预设原则

预设必须满足：

1. 使用当前模型已经支持并有测试覆盖的控制机制。
2. 控制效果在默认控制总览里可见。
3. 保留16线程/16 PARTID结构，但可以关闭未使用线程以降低运行时间。
4. 标明预期观察点，不承诺目标必然达到。

## 预设集合

### MC Hard BMAX + CBusy

目标：显示MC hard BMAX导致的hard block/带宽上限，以及CBusy返回后CPU effective OSTD下降。

关键设置：

- 单MC、低带宽、短队列、较高随机读压力；
- PARTID 0启用hard BMAX和CBusy；
- CBusy队列阈值较低，OSTD cap分三档下降。

### MC BMIN/QoS竞争

目标：显示两个PARTID争用MC时，BMIN和3-bit QoS改变调度偏好。

关键设置：

- 两个流竞争同一MC；
- PARTID 0启用BMIN和高QoS；
- PARTID 1为背景流，QoS较低且无BMIN。

### L3 CMIN/CMAX压力

目标：显示真实L3 lookup/fill下CMIN保护和CMAX增长限制带来的allocation denial、filtered/actual差异。

关键设置：

- 较小L3容量和随机读压力；
- PARTID 0配置CMIN保护；
- PARTID 1配置较低CMAX并施加背景压力。

### Mixed Overview

目标：让控制总览同时出现CPU OSTD、L3和MC的状态变化，作为端到端演示入口。

关键设置：

- 多个PARTID同时发压；
- PARTID 0保护，PARTID 1/PARTID 2背景流；
- 同时启用L3、MC QoS/BMAX和CBusy。

## UI行为

预设选择器放在顶部运行按钮附近。用户选择后点击应用，表单、16线程激励表和16 PARTID表更新；
页面显示toast提示，但不自动运行。

应用后用户仍可修改任意字段。重置按钮恢复服务端普通默认配置。
