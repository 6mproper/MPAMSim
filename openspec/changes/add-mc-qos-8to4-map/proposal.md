## 背景

当前MC共享buffer仲裁使用最终计算出的3-bit effective QoS，即0..7共8级。
后续硬件方案可能只实现更少的实际仲裁档位，例如把软件或MPAM侧3-bit配置压缩成4个物理流控档。
为了验证这种低PPA实现对带宽控制、BMIN/BMAX和防饥饿策略的影响，需要在MC增加一个可开关的8级到4级映射。

## 目标

- 新增MC全局配置开关，默认关闭以保持当前8级行为。
- 开启后，在MC完成base+BMIN-soft+deficit并钳位到0..7之后，按`01234567 -> 01112223`映射。
- MC最终仲裁比较使用映射后的4级QoS；相同映射档位仍使用rotating slot scan。
- 监控和UI同时显示raw 8级effective QoS和实际参与仲裁的mapped/final effective QoS。

## 非目标

- 不改变PARTID表中的3-bit QoS配置范围。
- 不改变L3 QoS调度、NoC QoS或CBusy生成规则。
- 不引入新的仿真模式或P1/P2专用数据面。
