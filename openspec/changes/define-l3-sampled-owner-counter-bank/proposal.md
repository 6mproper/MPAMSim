## 背景

当前L3 sampled-owner监控在代码中于监控边界遍历当前sample offset对应的set/way owner。
这种行为适合作为离散事件仿真，但容易被理解为硬件在一个周期内扫描大量tag/way SRAM。
真实硬件更合理的低PPA实现是：在fill、replacement、invalidate等line owner变化点维护
sampled-owner计数器，监控周期只读取计数器bank。

同时，UI中L3 occupancy仍使用“latest filtered”文案，容易让用户误以为CMIN/CMAX读取
带宽式递归滤波值。L3 occupancy是抽样状态量，控制输入应表述为published/control sampled owner。

## 目标

- 明确L3 sampled-owner监控采用counter-bank硬件近似，而不是监控边界瞬时扫描tag/way。
- 用fill/replacement时的owner变化维护`owner_count[offset][PARTID]`和监控组计数。
- rotating sampling在监控周期仅读取当前offset的counter bank。
- 将控制总览中L3 filtered文案改为sampled owner语义，MC继续保留latest filtered bandwidth语义。

## 非目标

- 不实现真实tag SRAM读端口、后台walker、scan latency或PPA面积模型。
- 不改变CMIN/CMAX的控制输入时序。
- 不改变MC bandwidth filtered语义。
