# PARTID 0高OSTD noisy-neighbor A/B说明

## 对比文件

- `noisy_neighbor_partid0_cbusy_off.json`：MC检测并返回PARTID 0的CBusy，CPU不执行OSTD cap。
- `noisy_neighbor_partid0_cbusy_on.json`：MC检测并返回PARTID 0的CBusy，CPU执行OSTD cap。

两份配置的仿真参数仅有`cpu_cbusy_response_enable`不同；描述文字不参与仿真。

## 场景配置

| 项目 | PARTID 0：noisy neighbor | PARTID 1：protected |
| --- | ---: | ---: |
| requester | cpu0.t0 | cpu1.t0 |
| 基础OSTD | 32 | 4 |
| offered load | 64 Gbps | 8 Gbps |
| request QoS | 3 | 3 |
| MPAM config QoS | 3 | 3 |
| BMIN | 关闭 | 3 Gbps |
| BMAX | 12 Gbps soft | 6 Gbps soft |
| CBusy生成 | 开启，cap=8/4/2 | 关闭 |

MC能力为`1 channel x 16 Gbps`。BMIN QoS提升、Soft BMAX QoS降档、aging、L3 QoS和L3 CBusy响应全部关闭，因此A/B带宽差异不能由这些控制动作解释。

PARTID 1以相同OSTD和激励单独运行时达到`6.246 Gbps`，高于`BMIN=3 Gbps`；共同运行时未达BMIN不是受害者自身offered load或OSTD上界不足导致。

## 运行方法

1. 打开仿真页面，点击“导入配置”，选择`noisy_neighbor_partid0_cbusy_off.json`。
2. 在“激励”页确认`cpu0.t0`的OSTD为32、`cpu1.t0`的OSTD为4，然后点击“开始仿真”。
3. 在结果页同时选择PARTID 0和PARTID 1，记录MC带宽、CPU effective OSTD和CBusy stall。
4. 导入`noisy_neighbor_partid0_cbusy_on.json`并重复运行；不要在两次运行之间手工修改其他参数。

两份文件使用页面导出配置的`mpamsim.config.parameters` schema，可由Web“导入配置”直接恢复。

## 当前代码参考结果

固定seed `20260713`、仿真`50 us`：

| 指标 | CPU不响应 | CPU响应 |
| --- | ---: | ---: |
| PARTID 0带宽 | 14.141 Gbps | 12.411 Gbps |
| PARTID 1带宽 | 1.761 Gbps | 3.492 Gbps |
| PARTID 1 BMIN达成率 | 58.7% | 116.4% |
| MC总带宽 | 15.903 Gbps | 15.903 Gbps |
| PARTID 0最小effective OSTD | 32 | 8 |
| PARTID 0 CBusy stall | 0 ns | 29280 ns |

判定反馈有效需要同时看到：MC产生CBusy、返回旁带到达CPU、PARTID 0 effective OSTD下降、CBusy stall增加、PARTID 0带宽下降、PARTID 1带宽越过BMIN、MC总带宽保持近似work-conserving。目标未达或过冲本身不是仿真失败。
