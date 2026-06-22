## 1. 规格

- [x] 1.1 创建中文OpenSpec change并严格校验。

## 2. 类型化契约

- [x] 2.1 实现Transaction、路由、延迟和MC仲裁状态。
- [x] 2.2 实现MonitorSnapshot、MonitorSample、ControlDecision和ControlEvent。
- [x] 2.3 实现接口协议族和组件能力描述。

## 3. 现有路径接入

- [x] 3.1 替换Request实现并消除MC动态属性。
- [x] 3.2 组件返回类型化监控快照，collector维持现有投影。
- [x] 3.3 policy和CBusy路径生成类型化控制事件。
- [x] 3.4 注册组件、校验能力并导出能力清单。

## 4. 验证

- [x] 4.1 添加事务、监控、控制、能力和兼容性测试。
- [x] 4.2 运行OpenSpec、Python测试和Web回归。
- [x] 4.3 同步运行目录并验证现有界面可继续仿真。
