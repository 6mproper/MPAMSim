## 为什么

当前L3虽然维护真实set/tag/way和1/8抽样误差，但CMIN/CMAX仍读取即时抽样owner；
Web时间线也主要显示导出周期平均值，尚不能区分物理实际值、raw MPAM样本和filtered控制输入。
地址到MC的交织规则也没有成为统一可配契约。

## 修改内容

- L3增加独立clock、256拍监控周期和history/current速率滤波权重。
- 每周期发布所有PARTID的raw抽样占用、control sampled占用、物理全量占用和raw/filtered访问带宽。
- CMIN/CMAX只读取发布并保存的control sampled-owner值，不读取即时或全量隐藏状态。
- 增加linear和XOR两种确定性MC地址交织配置。
- 控制效果和因果时间线显示目标、实际、raw、filtered、状态和控制事件，并允许独立选择PARTID。

## 影响能力

- `mpam-l3-control`：替换CMIN/CMAX控制输入。
- `soc-flow-simulation`：增加地址交织契约。
- `interactive-simulation-console`：增加监控配置和分层证据。

## 影响范围

- 修改CacheMSC、配置、地址映射、Web聚合和机制验证。
- 物理全量状态仅用于观测和误差计算，不得暗中参与CMIN/CMAX。
