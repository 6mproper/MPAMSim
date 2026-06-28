## 1. Specification
- [x] 1.1 定义MC QoS combiner字段、组合公式和默认行为。
- [x] 1.2 定义导入配置文件和对比结果的验收标准。

## 2. Implementation
- [x] 2.1 在配置schema、loader、validator和web config builder中加入combiner字段与request_qos。
- [x] 2.2 在MC共享buffer仲裁中通过单一combiner函数计算raw effective QoS。
- [x] 2.3 在monitor/timeline evidence中导出request/config/adjust/effective QoS。
- [x] 2.4 在UI中显示可配combiner字段和每条激励request_qos。

## 3. Comparison Assets
- [x] 3.1 生成六份可导入配置：两条路径 × replace/max/average。
- [x] 3.2 运行六个配置并输出清晰对比结果。

## 4. Verification
- [x] 4.1 增加MC combiner微测试覆盖replace/max/average路径差异。
- [x] 4.2 增加web config构建测试覆盖字段透传。
- [x] 4.3 运行OpenSpec和相关测试。
