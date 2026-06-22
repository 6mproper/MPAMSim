## 为什么

当前16个CPU线程各自维护独立OSTD，没有共享core资源；CBusy也按PARTID聚合所有MC，
导致MC0拥塞可能错误限制发往MC1的请求。这不符合总体规格`CPU-001`到`CPU-007`，
也无法验证SMT竞争和源端按目标MC限流。

## 修改内容

- 为同一core的硬件线程建立共享OSTD池。
- 保留每线程OSTD上限，并增加core总上限。
- 支持`shared`、`static_partition`和`reserve_borrow`三种core池策略。
- 使用确定性work-conserving round-robin选择有资格的待发线程。
- 在分配transaction ID前生成并保留待发地址，解析目标MC。
- CBusy按`(MC, PARTID)`限制新事务准入，不限制其他MC。
- 请求终止完成后同时释放thread和core OSTD。
- 扩展CPU监控，显示core池、目标MC和各类stall。
- Web新增core OSTD参数及完整控制说明。

## 影响能力

### 修改能力

- `soc-flow-simulation`：CPU requester改为8核16线程两级OSTD模型。
- `interactive-simulation-console`：增加core OSTD配置和监控语义。

## 影响范围

- 修改配置schema、loader、validator和Web builder。
- 新增core OSTD pool并改造generator/requester。
- 不在本change中实现私有cache、CPU pipeline或CHI request channel。
