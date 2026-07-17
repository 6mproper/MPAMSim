# CPU CBusy带宽反馈A/B复现说明

## 文件

- `cbusy_cpu_feedback_off.json`：MC生成并返回CBusy，但CPU只记录反馈，不执行OSTD限制。
- `cbusy_cpu_feedback_on.json`：MC生成并返回CBusy，CPU按PARTID执行OSTD限制。

两份文件的`parameters`仅有一个差异：

```text
cpu_cbusy_response_enable: false -> true
```

## 场景

```text
cpu0.t0 / PARTID 0 / victim         / 16 Gbps stream read
cpu1.t0 / PARTID 1 / noisy neighbor / 64 Gbps stream read
                         |
                         v
             MC0: 1 channel x 16 Gbps
```

PARTID 1配置`BMAX=4 Gbps`和CBusy档位。Soft BMAX的固定QoS降档为0，因此BMAX只作为CBusy带宽比例的比较基准，不直接改变MC调度。L3 CBusy响应和其他动态控制均关闭。

## UI运行步骤

1. 打开仿真页面，点击“导入配置”，选择`cbusy_cpu_feedback_off.json`。
2. 点击“开始仿真”，完成后进入“控制总览”。
3. 在MC目标带/监控/实际图中同时选择PARTID 0和PARTID 1，显示目标带、control input、actual和控制事件。
4. 在CPU区域选择PARTID 1，记录configured OSTD、effective OSTD和CBusy stall。
5. 导入`cbusy_cpu_feedback_on.json`并重复运行。
6. 两次截图使用相同的时间范围和带宽纵轴；建议MC带宽显示模式使用“插值曲线”，同时保留采样点。

## 通过判据

| 证据 | CPU不响应 | CPU响应 |
| --- | --- | --- |
| MC CBusy事件 | 必须存在 | 必须存在 |
| PARTID 1 effective OSTD | 保持32 | 降到12/4/2中的有效档位 |
| PARTID 1 CBusy stall | 0 | 大于0 |
| PARTID 1带宽 | 保持竞争份额 | 向4 Gbps附近下降 |
| PARTID 0带宽 | 约为竞争份额 | 明显抬升 |
| MC总带宽 | 接近16 Gbps | 仍接近16 Gbps |

## 当前代码参考结果

使用当前后端和相同seed试跑50 us得到：

| 指标 | CPU不响应 | CPU响应 |
| --- | ---: | ---: |
| PARTID 0带宽 | 7.813 Gbps | 11.274 Gbps |
| PARTID 1带宽 | 8.090 Gbps | 4.628 Gbps |
| MC总带宽 | 15.903 Gbps | 15.903 Gbps |
| MC平均队列 | 52.8 entries | 33.4 entries |
| PARTID 1最小effective OSTD | 32 | 4 |
| PARTID 1 CPU CBusy stall | 0 ns | 45232 ns |

以上数值用于回归参考，不是必须精确达到的设计目标。机制通过条件是因果链完整、动作方向正确并且相同配置能够确定性复现。该场景的累计P99在当前统计口径下没有明显改善，不能据此宣称尾延迟收益；若要验证延迟，需要增加排除启动瞬态的窗口P99。
