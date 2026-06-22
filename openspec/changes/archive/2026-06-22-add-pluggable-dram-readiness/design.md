## Context
MC共享buffer全候选架构。增加ready_mask作为QoS选择前的可选过滤器。

## Decisions
1. ready_mask方法返回每个slot是否ready
2. 默认实现全部ready
3. not-ready entry保留在buffer但不参与QoS
