## 1. 规格

- [x] 1.1 创建并严格校验中文OpenSpec change。

## 2. 配置

- [x] 2.1 增加core limit、policy和thread reserve类型化配置。
- [x] 2.2 增加Web控件、详细释义和校验。

## 3. CPU模型

- [x] 3.1 实现CoreOstdPool三种策略和round-robin。
- [x] 3.2 generator保留待发描述并在准入前解析目标MC。
- [x] 3.3 requester按thread、core、PARTID和MC分配及释放OSTD。
- [x] 3.4 CBusy按目标MC限制新事务。

## 4. 监控与验证

- [x] 4.1 导出core和每目标MC OSTD监控。
- [x] 4.2 添加共享、静态划分、reserve借用和MC隔离测试。
- [x] 4.3 运行OpenSpec、pytest和Web短仿真。
