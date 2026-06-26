## 1. 规格

- [x] 1.1 创建OpenSpec change说明删除软件慢闭环控制模式。
- [x] 1.2 更新基线OpenSpec和主spec中的控制模式边界。

## 2. 实现

- [x] 2.1 UI控制模式改为“无控制/有控制”两档。
- [x] 2.2 删除策略页签P99慢闭环参数输入。
- [x] 2.3 后端默认策略改为`static_mpam`，并把旧`closed_loop_qos`归一为`static_mpam`。
- [x] 2.4 删除软件慢闭环策略factory路径。
- [x] 2.5 更新UI帮助文案，说明P99目标只用于结果参考。

## 3. 验证

- [x] 3.1 运行OpenSpec strict。
- [x] 3.2 运行Web配置、元数据和机制测试。
