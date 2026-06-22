## Context

当前CBusy架构存在两条并行的MC→CPU通信通路：
1. 事务返回通路（RSP/DAT ring）— MC完成→L3 fill→CPU完成
2. CBusy反馈通路（独立定时事件）— MC定时采样→延迟回调→CPU更新本地表

两条通路延迟不同，CBusy可能在响应返回前或返回后到达，增加不确定性和验证复杂度。
目标是将CBusy合并到事务返回通路，消除分离控制旁路。

## Goals / Non-Goals

**Goals:**
- 删除`on_cbusy`独立定时回调通路
- MC在dispatch完成时采样2-bit CBusy，写入Transaction旁带字段
- RN在RSP或最后DAT flit到达时从Transaction读取CBusy并更新本地表
- 无返回时保持旧档位（陈旧状态容忍）
- 保留所有CBusy档位检测、滞回释放、准入判定逻辑

**Non-Goals:**
- 不改变CBusy档位判定算法
- 不改变CPU准入逻辑（`admission_block_reason`）
- 不改变OSTD限制语义
- 不让NoC读取CBusy字段进行仲裁
- 不改变Web监控界面中的CBusy显示

## Decisions

### 1. CBusy旁带字段 `Transaction.carry_cbusy_level: Optional[int]`

Transaction增加`carry_cbusy_level: int = 0`。
- 默认0，MC未设置时RN不更新
- MC仅对发往自身的事务写入非零值
- NoC不读取此字段，只作为flit payload移动

**替代方案：** 创建独立CBusy flit类型在RSP/DAT channel上发送。
**拒绝原因：** 增加NoC flit管理复杂度且CBusy更新与transaction完成天然绑定。

### 2. MC采样时机：dispatch完成时刻

MC在`_dispatch()`中，调度`on_complete`之前采样CBusy档位并写入transaction。
此时filtered带宽和queue状态均为最新发布值，无需额外定时器。

### 3. 旧评估定时器的处理

删除`_evaluate_cbusy()`和`_publish_cbusy()`方法及其定时调度。
删除MC构造函数的`on_cbusy`参数。
MC内部CBusy档位检测逻辑保留，但改为dispatch时按需调用。

简化为`_sample_cbusy(partid) -> int`方法：
- 输入PARTID
- 使用当前filtered带宽和buffer状态计算档位
- 返回2-bit level
- 不触发任何回调

### 4. RN更新时机：`_complete()`中

`Simulation._complete()`在收到终端RSP/DAT时被调用。
在此处从`request.carry_cbusy_level`读取，若非零则调用`requester.set_cbusy()`。

## Risks / Trade-offs

- **返回延迟等于CBusy反馈延迟** → 这是改善：旧方案有独立延迟参数，可能与实际拓扑不一致
- **长事务导致CBusy反馈陈旧** → 可接受：滞回释放已处理此场景，无返回时保持旧档位
- **L3 hit的请求不经过MC，无法获取CBusy** → Cache hit不更新CBusy，RN保持上次值，与CBusy设计意图一致（只反映MC拥塞）
