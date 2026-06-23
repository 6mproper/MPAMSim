## 1. 实现

- [x] 1.1 给常规workload增加`address_base_bytes`配置和生成逻辑。
- [x] 1.2 更新控制效果预设，让多PARTID场景使用不同地址窗口。
- [x] 1.3 修正UI中以`P<N>`显示PARTID的文案。
- [x] 1.4 增加P1最小闭环MVP回归测试。

## 2. 验证

- [x] 2.1 运行OpenSpec严格校验。
- [x] 2.2 运行相关pytest。
- [x] 2.3 启动/复用本地页面并用浏览器验证预设不再让`PARTID 1` MC带宽为0。
