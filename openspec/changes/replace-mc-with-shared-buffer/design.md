## Shared Buffer

固定slot保存valid entry，入队选择空slot。entry保存transaction、enqueue sequence和观测时间。
enqueue时间不参与调度。

## Readiness

```text
ready = valid AND not hard_blocked AND not ordering_blocked
```

同line较老/较新为read/read时可同时ready；任一包含write时新entry等待较老entry离开buffer。

## 监控

```text
period_ns = monitor_period_cycles * 1000 / mc_clock_mhz
raw_bw = serviced_bytes * 8 / period_ns
filtered = (history_weight * previous + current_weight * raw) / sum
```

周期边界先把上一已发布filtered锁存为control input，并用它更新UNDER_BMIN、
OVER_BMAX和HARD_BLOCK；随后计算并发布新的latest filtered，供下一次边界锁存。

## 滞回

- BMAX高于目标assert，低于`target*(1-h)` release；
- BMIN低于目标assert，高于`target*(1+h)` release；
- h=0关闭滞回。

## 调度

识别所有ready候选中的不同PARTID数量。只有竞争时：

- UNDER_BMIN加`bmin_qos_promote`；
- soft OVER_BMAX减`softlimit_qos_demote`。

hard OVER_BMAX始终从candidate删除。选择最高clamped 3-bit QoS，从上次grant slot之后旋转扫描。

## Service Deficit

可选每PARTID饱和计数器和grant_seen。每aging quantum：

- 无ready或hard block清零；
- 有grant减1；
- 无grant加1；
- QoS提升不超过配置步数。
