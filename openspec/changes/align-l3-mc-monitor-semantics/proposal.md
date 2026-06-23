## 背景

L3 occupancy是状态量，MC bandwidth是速率量。之前模型把L3 occupancy和MC bandwidth都放进
history/current滤波路径，容易让CMIN/CMAX读取被人为平滑的占用值；同时MC监控使用周期窗口清零计数，
还不是硬件式累计计数器语义。

## 目标

- L3 CMIN/CMAX默认读取上一监控边界锁存的sampled-owner occupancy绝对采样值。
- L3新增`fixed_first`和`rotating`两种采样模式；rotating按可配置监控周期在8个set内轮转offset。
- MC每PARTID使用63-bit累计服务字节计数器，在监控边界用累计差分计算sample bandwidth。
- MC使用`history_weight + current_weight = 1`的浮点权重计算filtered bandwidth，并将该值作为下一个控制周期输入。
- UI和spec区分L3状态量监控与MC速率量监控。

## 非目标

- 不实现全L3扫描作为控制输入；actual occupancy仍只用于验证。
- 不把L3 rotating sampling变成NoC或MC仲裁策略。
- 不扩展完整DRAM timing或OS接口。

## 风险

- L3 rotating模式会让短期control input随采样offset变化，更接近长期覆盖但可能更抖动。
- MC filtered bandwidth生效时序提前到刚结束周期的下一周期，部分旧测试的硬BMAX触发点会变化。
