## 1. 规格

- [x] 1.1 创建中文OpenSpec change并严格校验。

## 2. 配置与类型

- [x] 2.1 增加ring时钟、flit、槽位、hop、tie和node order类型化配置。
- [x] 2.2 增加Web配置、校验和完整算法说明。
- [x] 2.3 增加类型化flit、transfer和endpoint适配。

## 3. 数据面

- [x] 3.1 实现三条独立双向bufferless ring和确定性最短路由。
- [x] 3.2 实现目的端拒绝绕行、DAT逐flit注入与重组。
- [x] 3.3 接入CPU到L3、L3到MC及返回路径。
- [x] 3.4 在OSTD分配前接入REQ Ring注入许可。

## 4. 监控与验证

- [x] 4.1 导出每channel、方向、link、node和PARTID的flit及绕行证据。
- [x] 4.2 添加移动、路由、满Ring反压、拒绝绕行、DAT重组和确定性测试。
- [x] 4.3 运行完整pytest、OpenSpec和Web短仿真。
