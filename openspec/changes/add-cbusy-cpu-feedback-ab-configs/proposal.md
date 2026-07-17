# add-cbusy-cpu-feedback-ab-configs

## 背景

现有四组对照会同时改变BMAX、MC CBusy生成、CPU响应和L3响应，不能把带宽差异唯一归因到CPU执行CBusy反馈。需要两份可直接导入Web UI的单变量配置，证明MC返回CBusy后，CPU按PARTID收紧OSTD能够抑制noisy neighbor源端注入并释放MC带宽。

## 目标

- 提供CPU不响应CBusy和CPU响应CBusy两份可导入JSON配置。
- 两份配置除`cpu_cbusy_response_enable`外，仿真参数完全一致。
- MC在两组中都开启PARTID 1的CBusy生成，L3响应CBusy固定关闭。
- 使用BMAX作为带宽比较基准，但将Soft BMAX的QoS降档配置为0，避免MC调度动作混淆CPU反馈效果。
- 提供复现步骤、观察信号和已验证的参考结果。

## 非目标

- 不修改仿真模型、控制算法、数据模型或UI通路。
- 不声称该场景能够证明累计P99延迟改善。
- 不把达到BMAX目标作为通过条件；通过条件是反馈动作和带宽再分配可观察、可追踪。
