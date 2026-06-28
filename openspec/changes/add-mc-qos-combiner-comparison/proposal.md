# Change: Add MC QoS Combiner Comparison Configs

## Why
当前MC调度只把`mc_qos`作为base QoS，再叠加BMIN/BMAX/deficit delta。
用户需要比较`request_qos`、`mpam_config_qos`和`mpam_adjust_qos`在两条组合路径下的控制效果，
并能导入固定配置复现实验结果。

## What Changes
- 新增MC QoS combiner配置：
  - `mc_qos_combiner_order`: `adjust_before_request_combine`或`adjust_after_request_combine`
  - `mc_qos_combine_op`: `replace`、`max`或`average`
- 每条激励新增`request_qos`，生成的Transaction携带该请求QoS。
- MC仲裁trace导出`request_qos`、`mpam_config_qos`、`mpam_adjust_qos`、combiner配置和raw/final QoS。
- 输出六份可导入JSON配置，覆盖两条路径和三种组合方式。
- 输出一份对比结果摘要，说明哪类配置下路径2更能保留MC闭环调节的最后作用点。

## Non-Goals
- 不新增NoC QoS。
- 不新增validation_stage或P1/P2专用运行模式。
- 不让MC控制器读取actual语义状态。
- 不改变BMIN/BMAX监控时序和CBusy反馈时序。
