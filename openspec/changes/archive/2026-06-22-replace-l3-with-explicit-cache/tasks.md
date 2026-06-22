## 1. 规格

- [x] 1.1 创建中文OpenSpec change并严格校验。

## 2. 配置和接口

- [x] 2.1 增加miss/fill、MSHR、fill buffer、merge和replacement类型化配置。
- [x] 2.2 增加Web配置、校验和完整算法说明。
- [x] 2.3 把MC返回接入L3 fill endpoint。

## 3. L3数据面

- [x] 3.1 实现真实set/tag/way和LRU/PLRU。
- [x] 3.2 实现同line read MSHR merge和资源等待。
- [x] 3.3 实现fill、重复fill、CPBM/CMIN/CMAX替换及旁路。
- [x] 3.4 让1/8监控直接读取真实抽样set。

## 4. 验证

- [x] 4.1 添加hit/miss、替换、merge、owner、fill和监控误差测试。
- [x] 4.2 更新控制微基准并运行完整回归。
- [x] 4.3 运行OpenSpec和Web短仿真。
