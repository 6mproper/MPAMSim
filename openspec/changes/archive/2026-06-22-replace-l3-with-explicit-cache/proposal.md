## 为什么

当前L3命中由工作集和随机数推导，只在抽样set维护owner影子状态。实际hit/miss、替换、CPBM、
CMIN/CMAX和监控值没有共享同一tag/way事实，且miss不经过MSHR和fill资源。这无法验证同line
合并、真实替换冲突、fill压力和监控误差。

## 修改内容

- 用真实valid/tag/owner PARTID/PMG/last-touch set/way状态替换概率命中。
- 支持确定性LRU和mask-aware tree-PLRU。
- 增加miss detect、fill延迟、MSHR数量、fill buffer数量和同line read merge配置。
- 第一read miss建立MSHR并访问MC，后续同line read合并为waiter。
- MC返回DAT在L3 fill endpoint可接收时下Ring，经过fill latency后分配或旁路并完成所有waiter。
- 未合并重复fill发现line已存在时不创建重复tag、不修改owner并记录冗余访问。
- CPBM直接限制fill可选way；CMIN/CMAX作用于真实line替换。
- 1/8监控直接读取每8个set的第一个真实set，不再维护独立owner影子。
- 同时导出全set实际占用和1/8抽样估计，显示二者误差。

## 影响能力

- `soc-flow-simulation`：替换L3命中、miss、MSHR和fill数据面。
- `mpam-l3-control`：让CPBM/CMIN/CMAX作用于真实tag/way。
- `interactive-simulation-console`：增加L3资源配置和实际/抽样证据。

## 影响范围

- 修改CacheMSC、CacheConfig、Simulation MC返回端点、Web配置和监控。
- 256拍滤波值驱动CMIN/CMAX在后续监控change完成；本change先统一真实状态来源。
