## 1. 规格

- [x] 1.1 创建中文 OpenSpec change，规定控制总览 L3/MC 主图支持多 PARTID 同图对比。

## 2. UI

- [x] 2.1 在控制总览新增“同图对比 PARTID”多选控件和快捷动作。
- [x] 2.2 让 L3/MC 主图按多选 PARTID 叠加绘制目标带、control input、published/raw/actual和控制事件。
- [x] 2.3 更新图例，使 PARTID 颜色和曲线层线型分离表达。
- [x] 2.4 保持 CPU/L3/MC 状态卡仍使用当前单个 PARTID。

## 3. 验证

- [x] 3.1 更新静态测试覆盖新增控件。
- [x] 3.2 运行 JS 语法检查和相关 pytest。
