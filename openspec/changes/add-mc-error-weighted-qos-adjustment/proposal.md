## 背景

当前MC共享buffer调度在BMIN低于目标或soft BMAX超过目标时，使用固定QoS升档/降档常量。
这种模式简单、硬件实现低成本，但不能表达“超目标越多，调度修正越强”的方案探索。

## 目标

- 保留现有固定升降档能力，作为`fixed_step`模式。
- 新增`MC error-weighted QoS adjustment`模式，基于已发布并锁存的control bandwidth与BMIN/BMAX目标的相对误差计算QoS delta。
- 新模式只改变BMIN promote delta和soft BMAX demote delta，不改变hard BMAX、CBusy、service-deficit和8级到4级QoS映射的作用点。
- UI、配置文件、监控快照和验证摘要必须显示当前模式和误差参数，便于把仿真结果与配置对齐。

## 非目标

- 不新增P1/P2专用运行模式、数据面或UI通路。
- 不让控制器读取actual/debug带宽或当前周期未发布服务量。
- 不实现PID、软件闭环优化器、NoC QoS或DRAM bank级调度。
