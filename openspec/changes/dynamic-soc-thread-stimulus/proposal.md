# Change: SoC拓扑驱动激励槽位数量

## Why

当前Web控制台把激励固定为8C2T的16行，但SoC页签的核数和每核线程数应表示平台基础能力。
用户需要比较4C2T、8C2T、16C2T等不同平台规模时，激励表应由SoC拓扑自动展开，
避免SoC能力配置和workload配置产生语义重叠。

## What Changes

- `active_cores`和`threads_per_core`成为可编辑SoC基础拓扑参数。
- 激励表行数由`active_cores × threads_per_core`决定。
- slot到requester的映射改为`cpu{slot / threads_per_core}.t{slot % threads_per_core}`。
- 导入旧配置或切换拓扑时，激励行按slot保留已有配置，并对新增slot补默认激励、对超出slot裁剪。
- 16组PARTID控制保持固定，不随CPU线程数量变化。

## Impact

- 影响Web配置构建器、前端激励表、resctrl-like slot解析和相关规格/测试。
- 不改变仿真核心requester自动展开机制；后端loader已有`threads_per_core`支持。
