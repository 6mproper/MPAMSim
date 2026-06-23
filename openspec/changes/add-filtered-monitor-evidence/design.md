## L3监控平面

```text
period_ns = l3_monitor_period_cycles * 1000 / l3_clock_mhz
raw_sampled_count = 每个monitor group按当前sampling_offset读取一个set的owner way计数
control_sampled_count[k+1] = raw_sampled_count[k]
```

访问带宽使用同一周期和history/current权重，对抽样set访问字节乘monitor group比例后换算。

## 控制输入

周期k内的CMIN/CMAX只读取本地边界锁存的`control_input[k]`，
其来源是已发布并保存的`control_sampled_count`。
CPBM仍是每次fill直接执行的way eligibility。

## 三平面对照

- physical actual：全部真实set/tag/way，仅观测；
- raw MPAM：每个monitor group当前sampling_offset对应set的即时样本；
- latest filtered MPAM：速率类递归滤波发布值，用于UI和证据；
- control input：控制器实际读取的锁存监控值。

## 地址交织

```text
line = address / interleave_granularity_bytes
linear: mc = line % mc_count
xor:    mc = (line XOR (address >> xor_shift)) % mc_count
```

映射在CPU发射前确定，供目标MC OSTD/CBusy隔离使用。
