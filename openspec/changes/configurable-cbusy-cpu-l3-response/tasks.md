## 1. 规格

- [x] 1.1 把CBusy源端响应从旧的MC+PARTID索引改为PARTID聚合索引。
- [x] 1.2 定义CPU响应开关和关闭后的观察但不动作语义。
- [x] 1.3 定义L3响应开关、MSHR owner归因PARTID和新miss MSHR准入动作点。
- [x] 1.4 更新Web配置和算法说明要求。

## 2. 实现

- [x] 2.1 schema、loader和Web config builder增加CPU/L3响应开关。
- [x] 2.2 RequesterRuntime按PARTID聚合CBusy cap，关闭响应时不收紧effective OSTD。
- [x] 2.3 CacheMSC在fill返回时学习CBusy，并按PARTID cap限制新miss MSHR分配。
- [x] 2.4 控制事件保留feedback source MSC用于证据追踪。
- [x] 2.5 UI增加配置项和完整hover说明。

## 3. 验证

- [x] 3.1 更新CPU OSTD微测试，证明同PARTID跨目标MC受同一CBusy cap限制。
- [x] 3.2 增加CPU响应关闭微测试。
- [x] 3.3 增加L3 CBusy MSHR响应开启/关闭微测试。
- [x] 3.4 运行相关pytest和OpenSpec检查。
