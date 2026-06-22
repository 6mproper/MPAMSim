## Why
当前MC所有buffer entry始终ready。增加可插拔ready_mask接口，允许可选DRAM时序模型（channel/bank/row-open）在未来插入。

## What Changes
- MC增加ready_mask接口（默认全ready）
- QoS选择前过滤not-ready entry
- ready mask变化后仲裁自动唤醒
