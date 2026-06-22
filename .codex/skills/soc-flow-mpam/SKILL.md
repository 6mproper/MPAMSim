---
name: soc-flow-mpam
description: 继续设计、实现或审核本仓库的SoC系统流控与MPAM仿真模型。
---

# SoC Flow MPAM

处理本仓库的CPU OSTD、bufferless ring、L3、MC、MPAM监控与控制、CBusy、
配置界面或验证任务时使用本skill。

## 必读

1. 阅读`docs/Current_Model_SPEC.md`，它是权威架构和行为规格。
2. 阅读`docs/AI_Continuation_Plan.md`，按依赖顺序选择下一项工作。
3. 运行`openspec list --json`，读取当前active change的proposal、design、
   delta specs和tasks。

## 核心约束

- 暂不实现完整一致性和完整CHI，SNP可以保留inactive接口。
- CPU为8核16线程，两线程共享Core OSTD；终端RSP或DAT返回后才释放。
- NoC为REQ/RSP/DAT三条独立双向bufferless ring，不按PARTID/QoS仲裁。
- L3使用真实set/tag/way和LRU/PLRU；MPAM只监控每8个set的第一个set。
- CMIN/CMAX读取上一L3本地监控周期发布的filtered值，不读取physical actual。
- MC使用一个共享buffer，所有valid/ready entry参与3-bit QoS比较。
- 同QoS使用rotating slot；入队时间只观测，不参与默认仲裁。
- BMIN/BMAX读取上一MC本地监控周期发布的filtered带宽。
- soft BMAX无竞争时work-conserving；hard BMAX按整监控周期门控并允许过冲。
- 测试证明控制触发、动作和释放，不要求目标必然达到。
- Web、YAML和Python必须使用同一类型化schema。
- 所有OpenSpec正文使用中文。

## 证据规则

外部技术材料只使用：

- Arm、Linux、标准组织或供应商官方文档和官方技术支持；
- 同行评审论文；
- 专利。

不得用博客、二手教程或无来源总结作为架构事实。信息不足时明确写出缺口和
建议的证据获取方法。

## 完成模板

每个change必须：

1. 严格校验OpenSpec；
2. 添加机制级确定性测试；
3. 运行完整pytest；
4. 运行JS语法检查和浏览器短仿真；
5. 更新中文权威spec和配置指向说明；
6. 归档OpenSpec；
7. 形成单独git commit。
