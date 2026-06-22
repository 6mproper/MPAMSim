## 1. PARTID选择和结果总览

- [ ] 1.1 顶部增加PARTID多选条（1-16个checkbox或chip选择器）
- [ ] 1.2 紧凑结果总览卡片：issued/completed/P99/throughput/违规计数

## 2. 自适应时间图

- [ ] 2.1 L3占用图（target/actual/raw/filtered 四条线，选中的PARTID）
- [ ] 2.2 MC带宽图（target/actual/raw/filtered，选中的PARTID）
- [ ] 2.3 CBusy级别和OSTD限制图
- [ ] 2.4 共享时间游标联动

## 3. 控制事件时间线

- [ ] 3.1 底部共享控制事件时间线（横轴时间，标注setting change、CBusy transition、hard/soft block）
- [ ] 3.2 点击事件高亮对应时间点图表

## 4. 诊断入口

- [ ] 4.1 CPU OSTD诊断入口（Thread/Core pending/outstanding）
- [ ] 4.2 Ring slot occupancy诊断
- [ ] 4.3 L3 MSHR/fill buffer诊断
- [ ] 4.4 MC buffer/QoS诊断

## 5. 样式和响应式

- [ ] 5.1 CSS adaptive grid，desktop两列+时间线，mobile单列
- [ ] 5.2 PARTID用颜色区分，信号类型用线型/marker区分
- [ ] 5.3 target和actual单位一致

## 6. 验证

- [ ] 6.1 浏览器console无错误
- [ ] 6.2 单PARTID和多PARTID图例不混淆
- [ ] 6.3 小屏和desktop不重叠
- [ ] 6.4 运行完整pytest确认后端无回归
