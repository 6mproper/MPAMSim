# interactive-simulation-console 规格

## Purpose

定义当前已实现的本地Web控制台，用于配置、运行、动态观察、验证和导出SoC流控与
MPAM仿真，并规定由SoC拓扑展开的硬件线程、16组PARTID、因果时间线和上下文帮助等交互能力。
## Requirements
### Requirement: 配置文件导入导出

控制台 MUST 支持把当前表单配置导出为本地JSON文件，并支持从同类JSON文件导入后恢复表单。
导出内容 MUST 使用现有`collectParameters()`等价参数集，导入恢复 MUST 使用现有表单填充路径，
不得引入第二套配置模型。

#### Scenario: 导出当前配置

- **WHEN** 用户点击导出配置
- **THEN** 控制台 MUST 生成带`schema`、`version`、`exported_at`和`parameters`字段的JSON文件
- **AND** `parameters` MUST 包含SoC、激励、resctrl-like、MPAM和策略配置

#### Scenario: 导入配置文件

- **WHEN** 用户选择有效配置JSON文件
- **THEN** 控制台 MUST 用文件中的`parameters`恢复当前表单
- **AND** MUST 刷新配置诊断、上下文说明和可视PARTID选择

#### Scenario: 拒绝无效文件

- **WHEN** 用户导入无法解析或缺少参数对象的文件
- **THEN** 控制台 MUST 保持当前表单不变
- **AND** MUST 显示错误提示

### Requirement: 直接配置

控制台 MUST 允许用户配置SoC、由SoC拓扑展开的硬件线程激励、仿真时序、policy和16组PARTID控制，
无需修改源码。控制台 MUST 支持在MC调度算法参数中选择QoS调整模式：
`fixed_step`或`error_weighted`。

#### Scenario: 配置非默认PARTID

- **WHEN** 用户修改任意PARTID控制
- **THEN** 提交任务使用统一校验schema中的设置

#### Scenario: 配置MC QoS调整模式

- **WHEN** 用户选择`fixed_step`
- **THEN** 控制台 MUST 提交固定BMIN升档和softlimit降档参数
- **WHEN** 用户选择`error_weighted`
- **THEN** 控制台 MUST 提交BMIN/BMAX error weight、deadband、max delta和quantization参数

#### Scenario: 默认短窗口仿真

- **WHEN** 控制台加载默认配置
- **THEN** 默认仿真时间 MUST 为`5000ns`
- **AND** 默认控制周期 MUST 为`128ns`
- **AND** 控制周期输入 MUST 允许最小`128ns`

#### Scenario: 默认L3几何和快反馈开关

- **WHEN** 控制台加载默认配置
- **THEN** `l3_sets` MUST 默认为`20480`
- **AND** `l3_ways` MUST 默认为`20`
- **AND** `l3_qos_scheduler_enable` MUST 默认为`false`
- **AND** `l3_cbusy_response_enable` MUST 默认为`false`
- **AND** `cpu_cbusy_response_enable` MUST 默认为`false`

### Requirement: 动态执行

控制台 MUST 后台运行仿真，并在运行中更新进度和周期结果。

#### Scenario: 从界面运行

- **WHEN** 用户提交有效参数
- **THEN** UI经历running到done或failed且保持响应

### Requirement: MPAM结果可视化

控制台 MUST 只消费collector发布的类型化监控和控制事件投影，不直接读取NoC、L3、
MC或requester私有字段。

#### Scenario: 现有Web任务运行

- **WHEN** 类型化契约接入当前数据通路
- **THEN** 现有周期表格、控制记录和最终报告保持可用

### Requirement: 图表轴单位可见

控制台 MUST 在所有结果图表上显示横轴和纵轴的单位或类别语义。

#### Scenario: 时间序列图

- **WHEN** 控制台绘制P99、带宽、队列、L3控制效果、MC控制效果、QoS或P99目标时间序列
- **THEN** 横轴 MUST 标明时间单位
- **AND** 纵轴 MUST 标明对应指标单位

#### Scenario: 延迟分解柱状图

- **WHEN** 控制台绘制延迟分解柱状图
- **THEN** 横轴 MUST 标明类别语义
- **AND** 纵轴 MUST 标明延迟单位

### Requirement: 控制总览区分control input和latest filtered

控制总览 MUST 将控制器实际读取的锁存值显示为control input。L3 occupancy MUST 把最新发布值显示为
published sampled-owner；MC bandwidth等速率量 MAY 继续使用latest filtered。

#### Scenario: L3和MC主图

- **WHEN** 用户查看控制总览
- **THEN** 主图默认 MUST 显示目标带、control input、actual和控制事件
- **AND** L3 latest published sampled-owner SHOULD 可选显示
- **AND** MC latest filtered bandwidth SHOULD 可选显示
- **AND** raw sampled-owner、raw bandwidth和控制事件仍按显示层开关控制

#### Scenario: 文案区分

- **WHEN** UI解释raw、published、control input或actual
- **THEN** L3 occupancy文案 MUST 说明raw sampled-owner来自当前采样offset counter bank
- **AND** published sampled-owner MUST 说明为监控边界对外发布的sampled-owner快照
- **AND** MC bandwidth文案 MUST 说明filtered表示最新发布滤波带宽
- **AND** control input MUST 表示控制器读取的锁存监控值
- **AND** actual MUST 标注为验证用观测值，不得描述为控制输入

### Requirement: 结果文案不以达标作为验收

UI MUST 避免把目标达成或未达成表述为自动通过或失败。

#### Scenario: 目标偏离

- **WHEN** 控制目标未达、过冲或饱和
- **THEN** UI SHOULD 显示目标偏离、需解释或控制结果
- **AND** MUST NOT 将其显示为仿真失败

### Requirement: 报告访问

完成任务 MUST 提供同一次运行生成的HTML报告链接。

#### Scenario: 打开完成报告

- **WHEN** 仿真任务成功完成
- **THEN** UI提供该任务的HTML报告链接

### Requirement: 动态硬件线程激励编辑器

控制台 MUST 根据SoC页签的`active_cores × threads_per_core`显示激励行，并按slot稳定映射到
`cpuN.tM` requester。修改SoC核数或每核线程数后，控制台 MUST 自动裁剪或补齐激励行；
16组PARTID控制表 MUST 保持固定。

#### Scenario: 检查映射

- **WHEN** `active_cores=4`且`threads_per_core=2`
- **THEN** 编辑器 MUST 显示8行并覆盖`cpu0.t0`到`cpu3.t1`

#### Scenario: 扩展到16C2T

- **WHEN** `active_cores=16`且`threads_per_core=2`
- **THEN** 编辑器 MUST 显示32行并覆盖`cpu0.t0`到`cpu15.t1`

### Requirement: MPAM页签内resctrl-like软件组配置区

控制台 MUST 在MPAM页签内提供可选resctrl-like配置区，让用户通过CTRL_MON group、MON group、
`schemata`、`tasks`和`cpus_list`配置软件资源组，同时保留原始线程模式和原始
MPAM直接配置区。控制台 MUST NOT 保留独立resctrl页签。

#### Scenario: 默认不改变原始模式

- **WHEN** 控制台加载默认配置
- **THEN** resctrl-like模式 MUST 默认为关闭
- **AND** 当前SoC拓扑展开出的硬件线程激励仍直接使用原始PARTID/PMG配置

#### Scenario: 启用软件资源组

- **WHEN** 用户启用resctrl-like模式并提交仿真
- **THEN** 控制台 MUST 在提交前把软件组映射为当前硬件线程PARTID/PMG配置和16组PARTID控制
- **AND** MUST NOT 新增独立仿真运行模式或专用结果通路

#### Scenario: MPAM行提示软件接管

- **WHEN** 用户启用resctrl-like模式
- **THEN** MPAM页签中被启用CTRL_MON group映射到的PARTID行 MUST 显示“由resctrl接管”
- **AND** 提示 SHOULD 标明对应软件组名称
- **AND** 关闭resctrl-like模式后 MUST 隐藏该提示

### Requirement: resctrl-like软件接口可见

MPAM页签内的resctrl-like配置区 MUST 显示软件可见的mount/options、info、控制组树、内部
PARTID/PMG映射、`last_cmd_status`诊断和`mon_data`风格监控读数。

#### Scenario: 软件组映射可解释

- **WHEN** 用户修改`tasks`、`cpus_list`或MON group
- **THEN** UI SHOULD 显示每个组映射的内部PARTID/PMG
- **AND** SHOULD 显示任务优先于CPU默认组、否则落到root组的说明

#### Scenario: 监控读数复用现有结果

- **WHEN** 已有仿真结果且resctrl-like模式启用
- **THEN** `mon_data`视图 MUST 从现有L3/MC监控结果读取`llc_occupancy`、`mbm_total_bytes`和`mbm_local_bytes`风格读数
- **AND** MUST NOT 直接读取控制器私有actual状态作为软件监控输入

### Requirement: 每线程激励控制

每行 MUST 配置enable、PARTID、PMG、type、地址模式、依赖模式、发射选择、源队列深度、
rate、unit、size、read ratio、working set和可选P99 target。

#### Scenario: 独立修改

- **WHEN** 修改一行
- **THEN** 不隐式修改其他行

#### Scenario: 点击依赖字段

- **WHEN** 用户点击Dep、Issue或SrcQ列
- **THEN** 控制台说明pointer chain、eligible scan和源队列深度的行为边界

### Requirement: 稳定参考拓扑

Web参考场景 MUST 固定8核2线程，通用YAML和Python接口仍可配置拓扑。

#### Scenario: 加载Web默认值

- **WHEN** 控制台加载默认配置
- **THEN** 显示8核、每核2线程和16行激励

### Requirement: 上下文帮助

控制台 MUST 为每个可配置字段、动态表格子控件和选项提供点击打开的说明。
普通配置说明必须包含含义、单位、作用位置、模型影响、边界、示例和模型状态。
悬停、移出、focus和blur MUST NOT 打开或关闭说明。

#### Scenario: 检查普通配置

- **WHEN** 用户点击任意非控制配置
- **THEN** 显示该字段的完整释义且不修改配置值

#### Scenario: 关闭普通配置说明

- **WHEN** 普通配置说明已经打开
- **AND** 用户再次点击同一目标、点击空白处或按ESC
- **THEN** 说明关闭

#### Scenario: 新增字段遗漏说明

- **WHEN** 开发者新增默认配置字段但未注册元数据
- **THEN** 自动化覆盖测试失败并指出缺失字段

### Requirement: 激励类型说明

Type说明 MUST 区分stream、pointer chase、random read、mixed和burst。

#### Scenario: 点击Type控件

- **WHEN** 用户点击Type选择器
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

控制台 MUST 显示所选时间每个可见PARTID的控制状态。控制模式 MUST 只提供“无控制”和“有控制”两档。
“有控制”必须执行当前表单中已配置并开启的L3、MC、CPU和CBusy硬件/模型机制；控制台不得提供P99软件慢闭环
自动改写MC QoS或BMAX的控制模式。
控制模式的两档选择 MUST 使用两段式布局，不得保留空白第三段；L3 QoS、3-bit QoS、CBusy反馈和地址交织入口
MUST 明确标为算法说明入口，并与模式段分行显示，不得压缩到模式右侧或显示成控制模式子选项。

#### Scenario: 有控制模式

- **WHEN** 用户选择“有控制”
- **THEN** 提交参数中的policy MUST 为`static_mpam`
- **AND** 所有已配置硬件机制参数 MUST 进入resolved config
- **AND** 不得生成P99软件慢闭环运行时设置更新
- **AND** 控制模式UI MUST 只把“无控制”和“有控制”显示为模式段

#### Scenario: 无控制模式

- **WHEN** 用户选择“无控制”
- **THEN** 提交参数中的policy MUST 为`no_control`
- **AND** 仿真 MUST 保留监控和配置展示，但关闭L3/MC资源强制

#### Scenario: 旧闭环配置导入

- **WHEN** 导入旧配置中的policy为`closed_loop_qos`
- **THEN** 控制台 SHOULD 将其归一为`static_mpam`
- **AND** 不得显示或执行P99慢闭环参数

### Requirement: 每控制独立开关

PARTID编辑器 MUST 独立开关CPBM、CMIN、CMAX、BMIN、BMAX、MC QoS和CBusy。

#### Scenario: 修改单项开关

- **WHEN** 用户只关闭某一项控制
- **THEN** 其他控制开关和值保持不变

### Requirement: CBusy配置和证据

控制台 MUST 配置CBusy阈值、时序、CPU响应开关、L3响应开关、L3 QoS调度开关、
L3 CBusy QoS降档步长和OSTD cap，
并显示MC detector、CPU有效OSTD和L3响应证据。

#### Scenario: 观察CBusy

- **WHEN** MC提升某PARTID CBusy
- **THEN** MC视图显示detector，CPU视图显示有效OSTD和stall
- **AND** L3视图 SHOULD 显示CBusy level、MSHR cap、QoS demote、effective QoS和MSHR block证据

#### Scenario: 关闭响应动作

- **WHEN** 用户关闭CPU或L3 CBusy响应开关
- **THEN** 对应资源 MUST 仍可显示收到/生成的CBusy证据
- **AND** 对应资源 MUST NOT 执行该层的限流动作

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

当前控制台 MUST 配置L3 queue/parallelism、L3 QoS调度、L3 CBusy QoS降档和MC token、aging、BMIN提升及soft penalty。
L3 QoS调度 MUST 作为显式开关呈现，并提交为同一个布尔配置字段。
控制台 MUST 配置MC QoS 8级到4级映射开关。该开关关闭时MC按8级final QoS仲裁；
开启时MC按`01234567 -> 01112223`映射后的4级final QoS仲裁。

#### Scenario: 修改算法参数

- **WHEN** 用户修改受支持的算法参数
- **THEN** submitted config和监控快照使用新值

#### Scenario: 修改L3 QoS调度参数

- **WHEN** 用户修改L3 QoS调度开关或CBusy降档步长
- **THEN** submitted config和L3监控快照 MUST 使用新值

#### Scenario: 修改MC QoS映射

- **WHEN** 用户修改MC QoS 8级到4级映射开关
- **THEN** submitted config和MC监控快照 MUST 使用新值
- **AND** MC资源监控 SHOULD 显示raw effective QoS和实际final effective QoS

### Requirement: 内置控制验证

控制台 MUST 运行确定性CMIN、CMAX、BMIN、soft BMAX和hard BMAX微测试，
并显示检查和证据。

#### Scenario: 运行验证套件

- **WHEN** 用户启动算法验证
- **THEN** 各案例顺序执行并报告检查、预期行为和证据

### Requirement: 结构化算法说明

点击控制字段时，控制台 MUST 显示输入、保存状态、更新周期、决策规则、动作点、
恢复、交互优先级、前向进展、可观察证据和模型边界。悬停、移出、focus和blur
MUST NOT 打开或关闭算法说明。

#### Scenario: 点击控制字段

- **WHEN** 用户点击CMIN、CMAX、CPBM、BMIN、BMAX、MC QoS、CBusy或OSTD配置
- **THEN** 显示完整控制逻辑并标明当前实现与目标规格的差异

#### Scenario: 关闭控制字段说明

- **WHEN** 算法说明已经打开
- **AND** 用户再次点击同一目标、点击空白处、点击关闭按钮或按ESC
- **THEN** 算法说明关闭

#### Scenario: 控制说明不完整

- **WHEN** 控制算法元数据缺少任一必备逻辑章节
- **THEN** 自动化完整性测试失败

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

### Requirement: Core OSTD配置

控制台 MUST 配置thread limit、core limit、core OSTD policy和thread reserve，并提供完整
控制逻辑说明。

#### Scenario: 查看Core OSTD说明

- **WHEN** 用户点击任一Core OSTD配置
- **THEN** 说明共享状态、策略、准入、恢复、前向进展和监控证据

### Requirement: Bufferless Ring配置和证据

控制台 MUST 配置NoC clock、flit bytes、每方向link slots、hop cycles和tie方向，并说明
无buffer移动、注入反压、绕行、DAT重组和无NoC QoS规则。

#### Scenario: 查看Ring说明

- **WHEN** 用户点击任一Ring配置或监控列
- **THEN** 显示状态、时序、路由、动作、恢复、前向进展和证据定义

### Requirement: L3数据面资源配置和证据

控制台 MUST 配置replacement、miss detect、fill latency、MSHR、fill buffer和same-line merge，
并显示actual occupancy、sampled estimate、误差、merge和fill压力。same-line read merge默认 MUST 关闭。

#### Scenario: 查看MSHR说明

- **WHEN** 用户点击MSHR、fill或merge配置
- **THEN** 显示分配、等待、合并、owner、完成、前向进展和监控证据

### Requirement: MC周期控制配置和证据

控制台 MUST 配置MC clock、256拍周期、filter weights、滞回和service deficit，并显示
raw/latest filtered/control input BW、UNDER/OVER/HARD状态、candidate、grant和QoS饱和。

#### Scenario: 查看Hard BMAX说明

- **WHEN** 用户点击hard limit或MC monitor配置
- **THEN** 说明上一周期输入、过冲、整周期门控、滞回释放和buffer增长

### Requirement: 目标和监控平面时间证据

控制台 MUST 对所选一个或多个PARTID显示目标、physical actual、raw MPAM、published/filtered MPAM和控制状态。

#### Scenario: 多PARTID对比

- **WHEN** 用户选择多个PARTID
- **THEN** 图例使用PARTID颜色和信号线型共同区分曲线，且disabled不显示为0
