## 背景

当前Web控制台只提供原始线程模式：每个硬件线程直接配置PARTID/PMG，每个PARTID直接配置MPAM控制项。真实公开软件入口通常不是这样暴露硬件标签，而是通过Linux resctrl风格的控制组、监控组、`schemata`、`tasks`和`cpus_list`来表达资源策略。

## 目标

- 新增可选resctrl-like软件资源组配置页签，保留原始线程和MPAM页签。
- 支持CTRL_MON group、MON group、`schemata`、`tasks`、`cpus_list`和`mon_data`视图。
- 按公开resctrl语义实现任务优先于CPU默认组、否则落到root组。
- 在提交仿真前把软件组映射为现有16线程`PARTID/PMG`和16组PARTID控制，不新增仿真数据面。
- UI显示软件组到内部PARTID/PMG的只读映射和`last_cmd_status`风格诊断。

## 非目标

- 不实现完整Linux resctrl文件系统、内核权限、挂载生命周期或真实进程迁移。
- 不实现CDP、pseudo-locking、BMEC/ABMC、PERF_PKG_MON、SMBA、energytune或libvirt XML导入导出。
- 不新增P1/P2专用运行模式、数据模型或UI结果通路。
- 不改变控制器授权输入；控制器仍只能读取现有MPAM监控值、本地执行状态和配置状态。

## 证据边界

本阶段按Linux内核resctrl文档、Linux arm64 MPAM文档、Arm Neoverse参考MPAM文档和libvirt官方资源调优XML接口收敛软件入口抽象。若后续实现完整resctrl/libvirt，需要重新扩展OpenSpec并补充官方源码级行为验证。
