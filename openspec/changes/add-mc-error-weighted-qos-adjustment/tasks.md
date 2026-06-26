## 1. 规格

- [x] 1.1 定义MC QoS调整模式：`fixed_step`和`error_weighted`。
- [x] 1.2 定义error-weighted输入、deadband、weight、max delta和quantization。
- [x] 1.3 定义监控证据和UI配置要求。

## 2. 实现

- [x] 2.1 schema、loader、validator、Web config builder增加新参数。
- [x] 2.2 MC仲裁按模式计算BMIN/soft BMAX QoS delta，并把本次delta保存到Transaction仲裁状态。
- [x] 2.3 Web UI、帮助文案、配置诊断和验证摘要展示新模式。
- [x] 2.4 主中文spec和当前能力文档同步更新。

## 3. 验证

- [x] 3.1 微测试证明fixed_step保持当前固定升降档行为。
- [x] 3.2 微测试证明error_weighted BMAX按控制输入超限误差降档。
- [x] 3.3 微测试证明error_weighted BMIN按控制输入低于目标误差升档。
- [x] 3.4 运行相关pytest、语法检查和OpenSpec strict校验。
