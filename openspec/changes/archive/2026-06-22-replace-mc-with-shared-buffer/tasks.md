## 1. 规格

- [x] 1.1 创建中文OpenSpec change并严格校验。

## 2. 配置

- [x] 2.1 增加MC clock/period/filter、滞回和service deficit配置。
- [x] 2.2 增加Web控件、校验和完整算法说明。

## 3. 数据面和控制

- [x] 3.1 实现共享buffer、全候选和同line ordering。
- [x] 3.2 实现rotating slot 3-bit QoS调度。
- [x] 3.3 实现上一滤波周期驱动的BMIN、soft/hard BMAX和滞回。
- [x] 3.4 实现可选per-PARTID service deficit。
- [x] 3.5 让CBusy读取buffer count、filtered BW和hard block。

## 4. 验证

- [x] 4.1 添加全候选、ordering、QoS、滞回、hard sawtooth和deficit测试。
- [x] 4.2 更新机制验证并运行完整回归。
- [x] 4.3 运行OpenSpec和Web短仿真。
