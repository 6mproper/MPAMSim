## 1. 规格

- [x] 1.1 定义MC QoS 8级到4级映射开关、映射表和作用点。
- [x] 1.2 定义关闭映射时保持8级仲裁行为。
- [x] 1.3 定义raw/final QoS证据输出。

## 2. 实现

- [x] 2.1 schema、loader、config builder和Web UI增加MC QoS映射开关。
- [x] 2.2 MC仲裁在最终8级effective QoS之后应用可选映射，并用映射后值选择候选。
- [x] 2.3 监控快照导出raw effective QoS、final effective QoS、映射开关和映射事件。
- [x] 2.4 更新算法说明和资源监控显示。

## 3. 验证

- [x] 3.1 微测试证明关闭映射时2级可压过1级。
- [x] 3.2 微测试证明开启映射后1级和2级同档，按rotating slot scan选择。
- [x] 3.3 运行相关pytest、compileall和OpenSpec检查。
