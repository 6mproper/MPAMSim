## 1. 规格

- [x] 1.1 定义MC actual raw默认显示口径。
- [x] 1.2 定义actual MA为可选趋势层，且不参与控制输入。

## 2. 实现

- [x] 2.1 前端继续计算每PARTID尾随4窗口MC actual moving average。
- [x] 2.2 控制效果MC图和控制总览MC图默认使用完整窗口raw actual绘制actual。
- [x] 2.3 控制总览增加可选actual MA图层，默认关闭，保留尾部窗口不参与提示。

## 3. 验证

- [x] 3.1 JS语法和OpenSpec校验通过。
