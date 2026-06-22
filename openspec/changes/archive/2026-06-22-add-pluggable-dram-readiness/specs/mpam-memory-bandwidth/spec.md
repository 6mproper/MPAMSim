## ADDED Requirements

### Requirement: 可插拔DRAM Readiness
MC MUST 在QoS选择前使用_dram_ready(slot)过滤not-ready entry。默认实现全部ready，允许子类或未来扩展覆盖。
