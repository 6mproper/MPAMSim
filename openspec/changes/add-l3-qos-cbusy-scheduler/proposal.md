## 背景

MC已经能够生成PARTID维度CBusy，并通过返回路径让L3和CPU学习该反馈。
上一版L3只把CBusy用于新miss MSHR cap，属于硬限制动作。
为了观察更柔性的“中间缓存入口帮MC控带宽”机制，需要在L3增加类似MC的3-bit QoS调度：
当MC反馈某PARTID拥塞时，L3降低该PARTID在本地队列中的effective QoS，让其他PARTID更早进入lookup/MSHR/miss路径。

## 目标

- L3增加可配置QoS调度开关。
- L3 lookup入口队列和MSHR等待队列使用full-depth候选选择，选择effective QoS最高的请求，平级保持FIFO。
- L3 effective QoS复用现有PARTID 3-bit QoS配置作为base，按CBusy level乘以可配降档值进行demote并钳位到0..7。
- 该调度只影响L3本地新请求进入lookup/MSHR的顺序，不阻塞hit/fill/response，不新增NoC QoS能力。
- 导出L3 base/effective QoS、CBusy demote、candidate/grant证据，帮助判断它是否辅助MC带宽控制。

## 非目标

- 不实现完整L2响应。
- 不实现NoC QoS、credit、VC或上/下ring优先级。
- 不改变MC BMIN/BMAX/QoS算法。
- 不把L3 QoS调度作为带宽目标必达保证；目标未达、过冲和饱和仍作为控制结果观察。
