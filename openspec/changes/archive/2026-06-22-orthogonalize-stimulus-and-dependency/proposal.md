## Why

当前workload type隐含多个正交维度（地址模式、依赖关系、到达模式），导致pointer_chase和stream被混为一谈。将地址模式、依赖模式、到达模式拆分为独立配置维度，增加pointer_chain依赖（必须等前一事务返回后生成下一地址）和eligible_scan issue选择。

## What Changes

- 拆分workload type为独立维度：address_pattern、dependency_mode、arrival_mode
- 增加pointer_chain依赖模式：每条链同时最多一个未完成请求
- 增加source_queue_depth配置
- 保留旧workload type的自动推断兼容

## Capabilities

### Modified Capabilities

- `soc-flow-simulation`: 激励配置从type隐含改为显式多维度

## Impact

- `src/config/schema.py`: 增加address_pattern、dependency_mode、source_queue_depth字段
- `src/traffic/generator.py`: 实现pointer_chain等待逻辑和source queue
- `src/web/`: 配置界面支持新维度
