## 1. 规格

- [x] 1.1 创建OpenSpec change，区分L3 occupancy状态量和MC bandwidth速率量。
- [x] 1.2 更新L3规格，定义fixed/rotating sampled-owner采样和绝对占用控制输入。
- [x] 1.3 更新MC规格，定义63-bit累计计数器、差分采样、权重和为1和下一周期控制输入。

## 2. 实现

- [x] 2.1 增加L3 sampling mode和rotation period配置。
- [x] 2.2 L3 occupancy控制输入改为监控边界sampled owner绝对值。
- [x] 2.3 MC监控改为63-bit累计计数器差分。
- [x] 2.4 MC filtered bandwidth在监控边界计算后作为新控制周期输入。
- [x] 2.5 权重配置改为0..1且history/current之和等于1。

## 3. 验证

- [x] 3.1 增加/更新L3 fixed/rotating采样测试。
- [x] 3.2 更新MC hard BMAX时序和累计计数测试。
- [x] 3.3 运行OpenSpec strict、pytest、前端语法检查和页面检查。
