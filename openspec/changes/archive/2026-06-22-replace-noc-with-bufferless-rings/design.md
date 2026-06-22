## Ring状态

每个channel包含clockwise和counter-clockwise两个方向。每个方向保存：

- 每条link的固定flit槽；
- 在途flit及transaction/flit索引；
- 待注入端点flit；
- offered、injected、ejected、failed ejection、recirculation和hop计数。

Ring内部没有等待队列。待注入flit属于源端注入状态，不占Ring槽。

## 时序

```text
hop_delay_ns = hop_latency_cycles * 1000 / noc_clock_mhz
```

每个tick：

1. 所有link中的flit到达下一节点；
2. 到达目标节点时检查endpoint readiness；
3. 可接收则下Ring，否则进入该节点下一条link继续前进；
4. 其他flit无条件进入下一条link；
5. 空出的源link槽可供端点注入。

## 路由

根据`ring_node_order`计算两个方向距离，选择较短方向；等距时由`tie_direction`固定选择。
Ring不读取transaction priority、PARTID或MC QoS。

## DAT

REQ和RSP各为一个flit。DAT：

```text
flit_count = ceil(size_bytes / flit_bytes)
```

每个flit独立上Ring、移动和下Ring。全部flit下Ring后才调用一次transaction endpoint。

## 路径

```text
CPU --REQ--> L3
L3 miss --REQ--> MC
MC read complete --DAT--> L3 --DAT--> CPU
MC write complete --RSP--> L3 --RSP--> CPU
L3 hit read --DAT--> CPU
L3 hit write --RSP--> CPU
```

当前L3返回端点为过渡适配，不保存fill；真实MSHR和fill在后续L3 change中替换。

## 前向进展

- 在途flit永不停止；
- 目标不可接收只导致绕行；
- 至少保留一个slot且hop delay大于0；
- 有限注入和最终ready端点必须排空；
- 持续过载允许产生长期注入stall或绕行，不把性能目标未达判为模型错误。
