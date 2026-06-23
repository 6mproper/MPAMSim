## P0定义

P0完成只证明当前模型的控制机制可信，具体包括：

1. 各控制机制存在独立微测试，并证明机制动作生效；
2. 控制器只读取授权监控状态，不读取验证用actual状态；
3. 监控、决策和动作按周期传播，不允许零周期偷跑；
4. 至少两条最小端到端因果链可完整追踪；
5. 目标未达、过冲、饱和和不可行目标继续运行；
6. 相同输入和seed确定性复现；
7. 不新增阶段专用仿真模式、数据模型和UI通路。

## 授权状态边界

L3控制授权读取：

- PARTID配置：CPBM、CMIN、CMAX及其开关；
- 上一发布filtered sampled owner计数；
- 当前set/tag/way中用于执行替换的真实line状态。

L3控制不得读取physical actual occupancy作为CMIN/CMAX输入。actual只用于UI、导出和误差分析。

MC控制授权读取：

- PARTID配置：BMIN、BMAX、limit mode、MC QoS、CBusy及其开关；
- 上一发布filtered bandwidth状态；
- shared buffer valid/ready状态、同line顺序、CBusy detector输入、QoS aging状态。

MC控制不得读取理想化全局真值来提前判断目标是否可达。

## 最小因果链

P0至少保留两条可追踪链：

```text
L3链：
激励 -> miss/fill -> CPBM/CMIN/CMAX victim选择
-> allocation/eviction/bypass -> raw/filtered/actual曲线 -> UI事件
```

```text
MC/CPU链：
激励 -> MC带宽/队列监控 -> BMAX/QoS/CBusy决策
-> CPU OSTD变化 -> 带宽/延迟变化 -> UI事件
```

## 代码审视

当前代码审视结论：

- 独立微测试：已有CMIN、CMAX、MC QoS、BMIN、BMAX soft/hard、CBusy、Core OSTD、Ring和determinism相关测试；控制验证套件按机制生效判断，不要求目标必达。
- 未授权actual读取：L3 CMIN/CMAX使用`_filtered_sampled_counts`，actual occupancy只在snapshot导出；MC BMIN/BMAX使用filtered bandwidth状态。
- 时序：L3和MC都按monitor period发布filtered状态；hard BMAX已有上一周期门控测试；L3 filtered输入已有测试。
- 因果链：typed monitor sample、control decision、control event已有ID连接；UI已有控制总览、因果链和高级证据三层。
- 失败继续运行：目标未达、过冲、饱和和控制恶化属于CONTROL_OUTCOME，不作为异常；验证套件失败时应报告failed check而不是仿真失败。
- 确定性：固定seed仿真、Ring方向、MC slot轮转和地址交织有确定性要求和测试。
- 架构污染：P0不得引入专用模式或旁路；本change只修改规格和审视结论。
