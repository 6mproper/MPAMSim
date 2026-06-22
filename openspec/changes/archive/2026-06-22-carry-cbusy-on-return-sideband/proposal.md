## Why

当前MC通过独立定时事件向CPU发送CBusy反馈，引入了一条与实际RSP/DAT返回路径分离的控制旁路。
这使得CBusy反馈延迟独立于真实事务完成路径，CBusy可能在实际数据返回前或返回后到达，
成为额外的不确定延迟源。将CBusy采样到MC完成时刻并随返回flit携带，消除分离控制通路，
反馈延迟等于实际RSP/DAT返回延迟，旁带资源开销微不足道。

## What Changes

- 删除MC到CPU的独立定时`on_cbusy`回调通路
- MC在dispatch完成时采样`(MC, PARTID)`的2-bit CBusy，写入Transaction旁带字段
- RSP（write完成）或最后一个DAT flit（read完成）到达RN时，从Transaction读取CBusy并更新本地表
- CPU准入逻辑继续使用`(MC, PARTID)`匹配的本地反馈，不改变准入判定逻辑
- 无返回时（陈旧状态）保持旧档位不变
- 删除`MemoryControllerMSC`的`_evaluate_cbusy`、`_publish_cbusy`和`on_cbusy`参数
- 保留MC内部CBusy档位检测逻辑，仅改变采样触发点

## Capabilities

### New Capabilities

<!-- None — CBusy本身不是新能力，改变的只是反馈传输机制 -->

### Modified Capabilities

- `soc-flow-simulation`: CBusy反馈从独立定时事件改为RSP/DAT旁带，"CBusy控制有效OSTD"和"目标MC相关CBusy准入"requirement更新反馈机制描述

## Impact

- `src/ddr/memctrl.py`: 删除`_evaluate_cbusy`、`_publish_cbusy`、`on_cbusy`参数；在dispatch完成时采样CBusy并写入Transaction
- `src/contracts/transaction.py`: Transaction增加可选的`cbusy_level`旁带字段
- `src/sim/simulation.py`: 删除`_cbusy_feedback`方法和MC构造的`on_cbusy`参数；在`_complete`中从Transaction读取CBusy并调用`requester.set_cbusy`
- `src/traffic/requester.py`: `set_cbusy`保留，调用方式不变
- `src/web/server.py`, `src/config/schema.py`: CBusy采样配置字段可能简化
