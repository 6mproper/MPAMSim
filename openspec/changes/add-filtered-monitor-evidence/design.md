## L3监控平面

```text
period_ns = l3_monitor_period_cycles * 1000 / l3_clock_mhz
raw_sampled_count = 每8个set取第一个set的owner way计数
filtered_count[k] =
  (history_weight * filtered_count[k-1]
   + current_weight * raw_sampled_count[k]) / 256
```

访问带宽使用同一周期和权重，对抽样set访问字节乘8后换算。

## 控制输入

周期k内的CMIN/CMAX只读取周期边界已发布的`filtered_count[k-1]`。
CPBM仍是每次fill直接执行的way eligibility。

## 三平面对照

- physical actual：全部真实set/tag/way，仅观测；
- raw MPAM：每8个set首set的即时样本；
- filtered MPAM：递归滤波发布值，作为控制输入。

## 地址交织

```text
line = address / interleave_granularity_bytes
linear: mc = line % mc_count
xor:    mc = (line XOR (address >> xor_shift)) % mc_count
```

映射在CPU发射前确定，供目标MC OSTD/CBusy隔离使用。
