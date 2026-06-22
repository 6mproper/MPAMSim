## 为什么

当前NoC是一个带优先级heap的全局FIFO，只建模平均hop和串行化延迟。它不能表达已经确认的
三条CHI形态通道、双向最短路由、无buffer移动、目的端拒绝后的绕行，以及REQ上Ring对
CPU源端准入的反压。因此当前NoC延迟和OSTD因果关系不符合总体规格。

## 修改内容

- 用REQ、RSP、DAT三条独立双向bufferless ring替换旧全局FIFO。
- 每方向每链路维护固定flit槽，所有在途flit按hop周期同步前进。
- 最短方向路由，等距时使用固定tie方向。
- 目标端不可接收时flit继续绕行，并记录失败下Ring、完整绕环和附加延迟。
- Ring不读取PARTID QoS，不提供上Ring或下Ring优先级。
- DAT按`flit_bytes`拆分，逐flit注入并按transaction ID重组。
- CPU在分配OSTD前检查REQ注入槽；无槽时保持待发描述并记录`req_ring`源端stall。
- L3 miss通过REQ Ring到MC，L3 hit和MC完成通过RSP或DAT Ring返回CPU。
- 增加ring时钟、flit、槽位、hop和tie配置及完整说明。

## 影响能力

- `soc-flow-simulation`：替换NoC数据通路和延迟归因。
- `interactive-simulation-console`：增加bufferless ring参数与监控语义。

## 影响范围

- 修改NoC、仿真路由、generator准入、transaction监控、配置和Web说明。
- 本change不实现完整CHI opcode、SNP、一致性或L3 MSHR/fill。
