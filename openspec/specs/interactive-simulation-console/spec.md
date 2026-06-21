# interactive-simulation-console 规格

## Purpose

定义当前已实现的本地Web控制台，用于配置、运行、动态观察、验证和导出SoC流控与
MPAM仿真，并规定16线程、16组PARTID、因果时间线和上下文帮助等交互能力。

## Requirements

### Requirement: 直接配置

控制台 MUST 允许用户配置SoC、16线程激励、仿真时序、policy和16组PARTID控制，
无需修改源码。

#### Scenario: 配置非默认PARTID

- **WHEN** 用户修改任意PARTID控制
- **THEN** 提交任务使用统一校验schema中的设置

### Requirement: 动态执行

控制台 MUST 后台运行仿真，并在运行中更新进度和周期结果。

#### Scenario: 从界面运行

- **WHEN** 用户提交有效参数
- **THEN** UI经历running到done或failed且保持响应

### Requirement: MPAM结果可视化

当前控制台 MUST 显示每PARTID延迟/带宽、MSC queue、延迟归因、控制更新和16行监控。

#### Scenario: 检查结果

- **WHEN** 仿真完成
- **THEN** 监控视图包含全部16个PARTID及L3/MC证据

### Requirement: 报告访问

完成任务 MUST 提供同一次运行生成的HTML报告链接。

#### Scenario: 打开完成报告

- **WHEN** 仿真任务成功完成
- **THEN** UI提供该任务的HTML报告链接

### Requirement: 16线程激励编辑器

控制台 MUST 显示16行，固定映射`cpu0.t0`到`cpu7.t1`。

#### Scenario: 检查映射

- **WHEN** 编辑器初始化
- **THEN** 每个硬件线程恰好出现一次

### Requirement: 每线程激励控制

每行 MUST 配置enable、PARTID、PMG、type、rate、unit、size、read ratio、
working set和可选P99 target。

#### Scenario: 独立修改

- **WHEN** 修改一行
- **THEN** 不隐式修改其他行

### Requirement: 稳定参考拓扑

Web参考场景 MUST 固定8核2线程，通用YAML和Python接口仍可配置拓扑。

#### Scenario: 加载Web默认值

- **WHEN** 控制台加载默认配置
- **THEN** 显示8核、每核2线程和16行激励

### Requirement: 上下文帮助

配置类别、字段、表列、policy、结果类别和缩写 MUST 支持hover和键盘focus说明。

#### Scenario: 检查字段说明

- **WHEN** 用户指向或focus支持的字段
- **THEN** tooltip解释单位、行为或模型含义且不修改配置

### Requirement: 激励类型说明

Type说明 MUST 区分stream、pointer chase、random read、mixed和burst。

#### Scenario: 指向Type控件

- **WHEN** 用户指向或focus Type选择器
- **THEN** 说明每种类型的地址、局部性和burst特征

### Requirement: 监控组实时视图

控制台 MUST 按控制周期更新所有配置`(PARTID, PMG)`组。

#### Scenario: 运行中观察

- **WHEN** 收到周期快照
- **THEN** 更新L3估算占用和MC带宽，无需等待最终报告

### Requirement: 资源导向PARTID监控

控制台 MUST 提供CPU、L3和MC资源视图。

#### Scenario: CPU视图

- **WHEN** 选择CPU
- **THEN** 显示requester映射、OSTD、容量、issued/completed和backpressure

#### Scenario: L3视图

- **WHEN** 选择L3
- **THEN** 显示采样带宽、估算占用、hit rate、allocation denial和有效控制

#### Scenario: MC视图

- **WHEN** 选择MC
- **THEN** 显示带宽、利用率、延迟、BMIN/BMAX/mode/QoS和limit事件

### Requirement: PARTID独立显示选择

MUST 允许独立选择PARTID 0到15，并应用到表格和图表。

#### Scenario: 选择子集

- **WHEN** 只选择PARTID 2和7
- **THEN** 只显示2和7

### Requirement: 反馈控制状态

控制台 MUST 显示所选时间每个可见PARTID的反馈状态。

#### Scenario: 存在闭环更新

- **WHEN** 某PARTID已有运行时更新
- **THEN** 显示更新时间、target、field和reason

### Requirement: 每控制独立开关

PARTID编辑器 MUST 独立开关CPBM、CMIN、CMAX、BMIN、BMAX、MC QoS和CBusy。

#### Scenario: 修改单项开关

- **WHEN** 用户只关闭某一项控制
- **THEN** 其他控制开关和值保持不变

### Requirement: CBusy配置和证据

控制台 MUST 配置CBusy阈值、时序和OSTD cap，并显示MC detector和CPU有效OSTD。

#### Scenario: 观察CBusy

- **WHEN** MC提升某PARTID CBusy
- **THEN** MC视图显示detector，CPU视图显示有效OSTD和stall

### Requirement: 确定性机制实验

当前控制台 MUST 能从一个配置运行reference、BMAX-only、CBusy-only和combined案例。

#### Scenario: 运行比较

- **WHEN** 用户启动实验
- **THEN** 四个案例保持topology、stimulus、duration和seed一致

### Requirement: 因果时间线

时间线 MUST 按PARTID连接MC压力、CBusy、OSTD、stall、throughput、P99和控制事件。

#### Scenario: 跟踪CBusy变化

- **WHEN** 所选PARTID的CBusy变化
- **THEN** 同一时间线显示压力、反馈、OSTD和结果

### Requirement: 配置诊断

控制台 MUST 在运行前识别非法和高风险组合。

#### Scenario: BMIN过量

- **WHEN** 启用BMIN总和超过MC能力
- **THEN** 显示配置总和和能力警告

#### Scenario: 双重强限流

- **WHEN** Hard BMAX和严重CBusy cap同时启用
- **THEN** 警告可能产生额外吞吐损失

### Requirement: 流控算法配置

当前控制台 MUST 配置L3 queue/parallelism和MC token、aging、BMIN提升及soft penalty。

#### Scenario: 修改算法参数

- **WHEN** 用户修改受支持的算法参数
- **THEN** submitted config和监控快照使用新值

### Requirement: 内置控制验证

控制台 MUST 运行确定性CMIN、CMAX、BMIN、soft BMAX和hard BMAX微测试，
并显示检查和证据。

#### Scenario: 运行验证套件

- **WHEN** 用户启动算法验证
- **THEN** 各案例顺序执行并报告检查、预期行为和证据

### Requirement: 结构化算法说明

指向CMIN、CMAX、BMIN、BMAX、MC QoS、CBusy和OSTD时，控制台 MUST 显示
公式、触发规则、证据和边界。

#### Scenario: 指向控制算法

- **WHEN** pointer停留在已标记控制项
- **THEN** 显示锚定说明且不遮挡目标控件

### Requirement: PARTID控制效果概览

当前控制台 MUST 按16个PARTID汇总目标、实际值、QoS、P99和状态。

#### Scenario: 扫描控制状态

- **WHEN** 仿真存在周期数据
- **THEN** 每个PARTID显示目标、结果和状态

### Requirement: 所选PARTID完整趋势

选择一个PARTID时， MUST 按时间对齐L3、MC、QoS、P99、throughput和控制事件。

#### Scenario: 检查一个PARTID

- **WHEN** 用户选择一个PARTID
- **THEN** 相关目标、实际值和控制事件按统一时间轴显示
