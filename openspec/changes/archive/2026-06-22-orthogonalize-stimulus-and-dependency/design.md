## Context
当前workload type隐含地址模式和依赖关系。pointer_chase与stream使用相同的地址生成但无依赖约束。

## Decisions
1. 新增dependency_mode字段控制请求间依赖
2. pointer_chain模式通过检查requester.outstanding_by_partid实现
3. source_queue_depth预留但当前不限制（pending queue已有隐式深度1）
