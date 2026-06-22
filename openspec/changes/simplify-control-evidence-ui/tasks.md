## 1. 规格

- [x] 1.1 创建中文OpenSpec change草案并通过严格校验。

## 2. 信息架构

- [x] 2.1 将默认结果页收敛为控制总览、因果链和高级证据。
- [x] 2.2 将原有细分页签归并到高级证据或二级区域，避免默认平铺。

## 3. 控制总览

- [x] 3.1 增加CPU OSTD控制卡片，默认显示configured/effective OSTD、CBusy、outstanding和stall。
- [x] 3.2 增加MSC监控与控制卡片，默认显示L3和MC的目标、filtered监控、actual和控制状态。
- [x] 3.3 保留PARTID选择，支持单PARTID详细视图和多PARTID概览。

## 4. 图表和图例

- [x] 4.1 使用目标带、filtered主线、actual灰线和事件竖线替换默认多曲线叠加。
- [x] 4.2 raw monitor默认隐藏，增加显示raw采样误差的开关。
- [x] 4.3 多PARTID模式改为单信号小图、热力图或状态矩阵。
- [x] 4.4 禁止disabled控制绘制为0线。

## 5. 验证和交付

- [x] 5.1 增加或更新Web界面测试，覆盖默认字段、图例语义和hidden advanced telemetry。
- [x] 5.2 浏览器验证默认页无图例重叠、无曲线过载、算法说明仍可访问。
- [x] 5.3 运行OpenSpec严格校验、JavaScript检查和相关pytest。
- [x] 5.4 按项目约定上传Git。
