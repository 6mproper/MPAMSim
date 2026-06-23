# 设计：3-bit QoS、比例缓存控制和控制效果视图

## MC QoS

每个MC settings table包含`mc_qos`，范围为`[0, 7]`，7最高。
NoC请求优先级独立于MC QoS，本变更保持中性。

当前MC使用共享buffer全深度ready候选。每个ready entry计算：

```text
effective_qos = clamp(
    base_mc_qos
  + service_deficit_qos_steps
  + bmin_qos_promote when UNDER_BMIN and contended
  - softlimit_qos_demote when OVER_BMAX and contended,
  0, 7)
```

hard BMAX状态的entry从ready候选中排除。最高effective QoS获胜；
同档使用rotating buffer-slot scan。Monitor snapshot报告base/effective QoS、
promotion/demotion和候选/grant证据。

## 比例L3控制

`cmin_percent`和`cmax_percent`表示整个物理L3的比例。
每8个set采样1个set的模型把它们转换为聚合sampled-line目标：

```text
sampled_capacity_lines = ceil(sets / 8) * ways
reachable_percent = popcount(CPBM) / ways * 100
effective_cmin = min(configured_cmin, reachable_percent)
effective_cmax = min(configured_cmax, reachable_percent)
cmin_lines = ceil(sampled_capacity_lines * effective_cmin / 100)
cmax_lines = floor(sampled_capacity_lines * effective_cmax / 100)
```

CMIN是需求填充后的replacement保护，不做预分配。CMAX阻止聚合sampled ownership
继续超过比例上限。CMIN总和超过100%无效；CMAX总和可以超过100%。

## 控制效果

每个PARTID沿四层评估：

```text
configured target -> enforcement/control_input state -> achieved resource share
                  -> workload result and control cost
```

总览报告目标、control input、latest filtered、actual和运行结果。选中PARTID视图对齐：

- L3 control input/latest filtered/actual share与CMIN/CMAX目标；
- MC control input/latest filtered/actual bandwidth与BMIN/BMAX目标；
- base/effective MC QoS和调整证据；
- P99目标/实际、吞吐、队列、CBusy和OSTD证据；
- 带时间戳的控制事件和控制结果。

CMIN和BMIN只在有需求和可观测竞争时解释。Soft BMAX归类为无竞争借用或竞争下降档，
不简单标记为cap违反。

## 算法说明

统一help registry提供标题、模型版本、作用范围、公式、规则、证据和边界。
指向控制或指标时打开可滚动说明窗口。同一registry用于字段、流程阶段和结果列。
