## 1. 规格

- [x] 1.1 定义尾部不完整窗口MC actual的显示口径。
- [x] 1.2 明确控制输入和原始证据不受影响。

## 2. 实现

- [x] 2.1 在MSC行中导出snapshot `interval_ns`。
- [x] 2.2 前端识别短于`control_interval_ns`的MC actual窗口。
- [x] 2.3 控制效果和控制总览MC带宽图排除短窗口actual点和autoscale贡献。
- [x] 2.4 表格/概览卡片对排除点显示“尾部窗口不参与”。

## 3. 验证

- [x] 3.1 增加测试确认MC final snapshot暴露短窗口`interval_ns`。
- [x] 3.2 JS语法、OpenSpec和相关pytest通过。
