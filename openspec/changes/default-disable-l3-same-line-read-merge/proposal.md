## 背景

当前L3 same-line read miss合并能力用于模拟多个并发read访问同一cache line时共享第一笔MSHR和MC请求。
它是有用的可配能力，但默认开启会削弱默认场景下MSHR、MC带宽、CBusy和源端OSTD的压力可见性。

## 目标

- 默认关闭L3 same-line read miss合并。
- 保留用户显式开启该能力的配置入口和已有行为。
- 让Web默认参数、YAML缺省加载、schema缺省和UI checkbox保持一致。
- 更新spec和说明文字，明确默认关闭是为了保留独立miss压力。

## 非目标

- 不删除same-line read merge能力。
- 不改变显式配置`merge_same_line_misses: true`时的合并语义。
- 不改变MC同line ordering规则。

## 风险

- 默认场景的MC请求数和带宽压力可能上升，这是本次修改的预期效果。
- 部分旧实验如果依赖默认合并，需要显式打开该开关才能复现旧结果。
