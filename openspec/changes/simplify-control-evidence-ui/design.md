## 设计目标

默认界面回答三个问题：

1. CPU源头有没有被控制。
2. L3/MC这些MSC监控到了什么并执行了什么控制。
3. 控制动作是否形成可见因果链，并解释目标未达、过冲、饱和或无效。

## 信息架构

结果区默认提供三个一级页签：

- `控制总览`：面向控制验证的主视图。
- `因果链`：按时间串联监控、控制动作和性能变化。
- `高级证据`：面向模型调试和问题定位的展开视图。

原有`资源监控`、`控制效果`、`监控组`、`MPAM监控`、`MSC`、`控制记录`中的内容不直接平铺；
它们按用途归入以上三个层级。高级证据可以继续细分CPU、L3、MC、NoC和日志。

## 控制总览

### CPU OSTD控制区

默认按PARTID聚合，必要时展开到core/thread和目标MC。

必须显示：

- configured OSTD；
- effective OSTD cap；
- 当前outstanding和峰值；
- CBusy level及来源MC；
- source stall/backpressure；
- issued/completed。

若CBusy按目标MC生效，显示必须保留`(PARTID, target MC)`维度，避免把MC0反馈误读为全局限制。

### MSC监控与控制区

L3默认显示：

- CMIN/CMAX目标范围；
- filtered MPAM占用；
- physical actual占用；
- allocation denial和protected eviction；
- 当前控制状态。

MC默认显示：

- BMIN/BMAX目标范围；
- filtered MPAM带宽；
- actual service带宽；
- queue depth；
- base/effective QoS；
- soft/hard状态；
- CBusy level。

raw monitor、candidate/grant、deficit、MSHR和fill buffer默认隐藏到高级证据。

## 图形语义

默认图例固定为以下语义：

- 绿色目标带：配置或生效目标范围；
- 粗蓝线：控制实际读取的filtered MPAM monitor；
- 细灰线：physical actual或service actual；
- 橙色竖线：控制动作或状态切换事件。

raw monitor默认隐藏，只有用户打开`显示raw采样误差`后才显示为点状线。
disabled控制不得画成0线；未配置目标应显示为无目标状态。

## 单PARTID与多PARTID

单PARTID模式显示完整时间曲线和事件标记。

多PARTID模式默认不把所有信号混画到一张图：

- 只比较一种信号时，可用多PARTID小图；
- 比较控制状态时，优先用热力图或状态矩阵；
- 同一张图中不得同时混合多个PARTID和多个信号语义。

## 因果链

因果链按统一时间轴展示：

1. MSC压力：L3替换压力或MC queue/BW压力；
2. 控制输入：filtered monitor与目标带的关系；
3. 控制动作：CMIN/CMAX、BMIN/BMAX、QoS或CBusy状态变化；
4. CPU响应：effective OSTD、outstanding、stall和发射压力；
5. 结果：P99、吞吐和完成率。

目标未达、过冲、控制饱和或控制导致性能下降都必须继续显示，不视为仿真失败。

## 高级证据

高级证据保留以下内容：

- raw MPAM和physical误差；
- L3 MSHR/fill buffer/merge/bypass；
- MC candidate/grant/service deficit；
- NoC ring flit、绕行和下Ring失败；
- 完整控制日志；
- 原始表格导出。

高级证据用于解释异常，不作为默认判断控制效果的第一入口。
