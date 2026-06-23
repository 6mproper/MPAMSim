## 1. 规格

- [x] 1.1 创建中文OpenSpec change，定义P0/P1时序前置门槛。
- [x] 1.2 更新`soc-flow-simulation`规格，固定监控双缓冲顺序。
- [x] 1.3 更新L3和MC规格，明确控制读取control input而不是同边界新filtered。
- [x] 1.4 更新当前模型中文spec，修正`MON-003`歧义。

## 2. 实现

- [x] 2.1 L3拆分`filtered_sampled`发布值和`control_sampled`控制输入。
- [x] 2.2 MC拆分`filtered_bandwidth`发布值和`control_bandwidth`控制输入。
- [x] 2.3 BMIN/BMAX、hard block和CBusy带宽项改读control input。
- [x] 2.4 保持现有raw/filtered/control input/actual UI和导出通路，不新增阶段专用通路。

## 3. 验证

- [x] 3.1 增加/更新L3微测试，证明刚发布filtered不会同边界驱动CMIN/CMAX。
- [x] 3.2 增加/更新MC微测试，证明BMAX hard block不会同边界偷跑。
- [x] 3.3 运行OpenSpec strict校验和相关pytest。
