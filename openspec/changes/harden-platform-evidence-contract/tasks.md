## 1. 规格

- [x] 1.1 创建OpenSpec change，定义平台证据契约。
- [x] 1.2 将timing freeze上移为P0/P1前置门槛。
- [x] 1.3 定义`control_input` telemetry语义和`CONTROL_OUTCOME`契约。
- [x] 1.4 定义`ControlContext`作为后续控制能力扩展边界。
- [x] 1.5 清理旧OpenSpec中filtered=控制读取值的残留描述。

## 2. 实现

- [x] 2.1 增加`MetricSemantic.CONTROL_INPUT`并映射`control_*`指标。
- [x] 2.2 增加`ControlOutcome`和`ControlContext`类型。
- [x] 2.3 让L3/MC内部控制状态切换复用`ControlEvent`。
- [x] 2.4 UI控制总览显示control input，并将filtered标为latest filtered。
- [x] 2.5 UI目标状态文案改为机制生效/目标偏离，不再暗示目标达成即验收通过。

## 3. 验证

- [x] 3.1 测试`control_*`样本语义为`control_input`。
- [x] 3.2 测试P1预设导出L3/MC内部控制事件和可解析control input样本。
- [x] 3.3 运行OpenSpec、pytest和浏览器检查。
