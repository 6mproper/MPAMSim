# add-noisy-neighbor-partid0-ab-configs

## 背景

需要复现一个严格的带宽noisy-neighbor场景：PARTID 0拥有较大的CPU OSTD和较高的内存带宽需求，PARTID 1拥有较小的CPU OSTD和较低但可独立达到的BMIN。两者竞争同一个MC时，PARTID 0可能使PARTID 1低于BMIN；MC对PARTID 0返回CBusy并由CPU执行OSTD cap后，应释放带宽给PARTID 1。

## 目标

- 提供两份Web UI可直接导入的JSON配置，显式配置每个requester的基础OSTD。
- 激励表新增每requester基础OSTD，旧JSON继续继承SoC默认值。
- 两组保持拓扑、激励、MPAM目标、MC检测和seed一致，只切换CPU是否响应CBusy。
- BMIN QoS提升、Soft BMAX QoS降档、aging和L3响应均关闭，避免其他动作解释结果。
- 证明受保护流单独运行时具备达到BMIN的能力，目标未达不是自身OSTD或offered load不足导致。

## 非目标

- 不新增仿真模式或结果通路；复用现有激励表、requester类型和JSON导入通路。
- 不把低于BMAX误判为目标失败；受保护流的判据是BMIN。
- 不声称反馈必然精确收敛到BMAX。
