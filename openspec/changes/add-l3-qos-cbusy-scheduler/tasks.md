## 1. 规格

- [x] 1.1 定义L3 QoS调度作用点和前向进展边界。
- [x] 1.2 定义MC CBusy到L3 effective QoS demote的公式。
- [x] 1.3 定义UI配置和证据导出要求。

## 2. 实现

- [x] 2.1 schema、loader和Web config builder增加L3 QoS调度开关和CBusy降档步长。
- [x] 2.2 CacheMSC lookup入口队列按effective QoS选择请求，平级FIFO。
- [x] 2.3 CacheMSC MSHR等待队列按effective QoS选择可准入请求，CBusy cap阻塞请求不阻塞其他可准入请求。
- [x] 2.4 L3监控导出base/effective QoS、CBusy demote、candidate/grant证据。
- [x] 2.5 UI配置和点击说明更新。

## 3. 验证

- [x] 3.1 微测试证明L3 QoS能让高QoS请求越过低QoS队首。
- [x] 3.2 微测试证明MC返回CBusy会降低L3 effective QoS并改变调度顺序。
- [x] 3.3 微测试证明关闭L3 QoS调度后保持FIFO。
- [x] 3.4 运行相关pytest、compileall和OpenSpec检查。
