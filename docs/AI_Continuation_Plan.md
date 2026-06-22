# MPAMSim后续编码交接计划

## 1. 交接基线

本计划基于2026-06-22代码状态，权威架构规格为
`docs/Current_Model_SPEC.md`。后续实现必须继续使用OpenSpec，中文编写
proposal、design、delta spec和tasks。

当前已完成：

1. 类型化Transaction、监控和组件能力契约；
2. 8核16线程、Thread/Core两级OSTD和三种Core共享策略；
3. REQ/RSP/DAT三条独立双向bufferless ring；
4. 真实L3 set/tag/way、LRU/PLRU、MSHR、fill buffer和同line read合并；
5. L3每256本地拍raw/filtered监控，CMIN/CMAX读取上一发布值；
6. linear/XOR地址到MC交织；
7. MC共享buffer全候选、同line最小顺序、3-bit QoS和rotating slot；
8. MC每256本地拍raw/filtered带宽、BMIN、soft/hard BMAX、滞回和service deficit；
9. 16个PARTID配置、监控、目标值和实际值Web显示；
10. 确定性机制测试、完整回归和OpenSpec归档流程。

必须保持的设计约束：

- 不把完整一致性和完整CHI作为当前范围；
- 不让physical actual或当前窗口隐藏状态暗中参与MPAM控制；
- 自动化验证控制是否触发、执行和释放，不要求目标必然达到；
- Ring不提供PARTID/QoS上下Ring能力；
- MC QoS只在MC本地生效；
- 新能力原位替换旧模型，不建立第二套完整数据通路；
- 所有外部技术结论只使用官方文档、官方技术支持、论文或专利。

## 2. 开发顺序

以下步骤按依赖排序。每一步单独建立OpenSpec change，严格校验、测试、
浏览器验收、归档和提交后，才进入下一步。

### 步骤1：CBusy改为RSP/DAT旁带反馈

建议change：`carry-cbusy-on-return-sideband`

目标：

- 删除MC到CPU的独立定时反馈事件；
- 在MC完成时采样`(MC, PARTID)`的2-bit CBusy；
- 随RSP或最后一个DAT flit返回RN；
- RN只更新匹配目标MC和PARTID的本地反馈表；
- 保留返回延迟和无返回时的陈旧状态。

主要文件：

- `src/contracts/transaction.py`
- `src/ddr/memctrl.py`
- `src/noc/fabric.py`
- `src/sim/simulation.py`
- `src/traffic/requester.py`
- `src/monitor/collector.py`

验证：

- MC状态变化但无返回时RN不更新；
- 返回到达前CPU继续使用旧档位；
- MC0/PARTID2反馈不限制MC1或其他PARTID；
- RSP、单DAT和多flit DAT都只在终端返回时更新一次；
- CBusy不取消已发请求、不阻塞响应、不修改MC QoS。

完成条件：

- 删除`on_cbusy`直接回调数据通路；
- CPU时间线能显示MC采样、返回携带、RN生效三个时间点；
- 全量测试通过。

### 步骤2：资源本地监控历史和稳定因果ID

建议change：`record-resource-local-monitor-history`

目标：

- 不只在全局`control_interval_ns`保存快照；
- L3和MC每个本地监控周期都保存16个PARTID的periodic state sample；
- 离散保存monitor publish、decision、action effective、release事件；
- 用稳定ID关联观察、决策、动作和后续结果。

主要文件：

- `src/contracts/telemetry.py`
- `src/monitor/collector.py`
- `src/cache/cache_msc.py`
- `src/ddr/memctrl.py`
- `src/output/`或现有导出模块

建议字段：

```text
observation_id
decision_id
action_id
resource_id
local_cycle
time_ns
partid
metric
semantic
cause_id
```

验证：

- 所有16个PARTID每周期都有记录，包括0活动；
- UI隐藏PARTID不影响采集；
- disabled使用null/状态字段，不伪装成0；
- 相同seed和配置生成相同ID和顺序；
- 监控采集不得改变调度结果。

### 步骤3：控制效果工作区收敛

建议change：`simplify-control-evidence-workspace`

目标：

- 用一个配置驱动主工作区替代大量等权页签；
- 默认只突出启用控制、活动PARTID、违规、饱和和不可达状态；
- 支持一个或多个PARTID、单实例或聚合视图；
- 共享时间游标下同时显示target、effective target、physical actual、
  raw MPAM、filtered MPAM、control state和event marker。

主界面建议保留：

1. PARTID和资源选择条；
2. 紧凑结果总览；
3. 3到5张自适应时间图；
4. 一条共享控制事件时间线；
5. CPU/Ring/L3/MC/filter/CBusy诊断入口。

主要文件：

- `src/web/static/index.html`
- `src/web/static/app.js`
- `src/web/static/styles.css`
- `src/web/server.py`

验证：

- 单PARTID和多PARTID图例不混淆；
- PARTID用颜色，信号类型用线型/marker区分；
- target和actual单位一致；
- 小屏和桌面不重叠；
- Playwright截图和浏览器console无错误。

### 步骤4：激励维度正交化和真实依赖

建议change：`orthogonalize-stimulus-and-dependency`

目标：

- 拆分当前workload type隐含的多个维度；
- 独立配置address pattern、operation mix、dependency mode、
  arrival mode和issue selection；
- pointer chase必须等待前一返回后产生下一地址；
- eligible scan只在已生成的独立请求窗口中选择可发事务；
- 增加可配source pending queue深度。

建议配置：

```yaml
address_pattern: sequential | uniform_random | hotset | stride
operation_mix: read | write | mixed
dependency_mode: independent | pointer_chain
arrival_mode: fixed | poisson | burst
issue_selection: fifo | eligible_scan
source_queue_depth:
pointer_chains:
```

验证：

- pointer chain的每条链同时最多一个未完成依赖请求；
- independent模式可形成多OSTD；
- eligible scan不生成新地址，只选择ready descriptor；
- 旧Web配置通过明确转换规则兼容。

### 步骤5：CHI形态事务类别和完成语义

建议change：`complete-chi-shaped-transaction-semantics`

目标：

- 保持一致性关闭，SNP通道接口存在但inactive；
- 明确REQ/RSP/DAT用途和完成条件；
- read在最后DAT返回后释放CPU OSTD；
- write在终端RSP返回后释放；
- 支持跨line请求拆成line-aligned child transaction并聚合完成。

验证：

- 不允许MC服务完成时提前释放OSTD；
- 多flit DAT只在重组完成后释放；
- parent只在所有child完成后完成；
- 不宣称CHI compliance。

### 步骤6：可插拔MC DRAM readiness

建议change：`add-pluggable-dram-readiness`

目标：

- 保持共享buffer全候选架构；
- 在QoS前增加可替换`ready_mask`接口；
- 默认模型继续全部ready；
- 可选增加channel/bank/row-open的低复杂度时序模型；
- 不用enqueue timestamp做默认QoS比较。

验证：

- not-ready entry不参与QoS，但保留buffer；
- ready mask变化后仲裁自动唤醒；
- 同line write顺序仍优先于DRAM ready；
- 默认模型结果与当前基线兼容。

### 步骤7：resctrl风格软件配置接口

建议change：`add-resctrl-like-software-groups`

目标：

- 保留当前thread直接配置PARTID/PMG模式；
- 新增命名CTRL_MON group、MON group、task/CPU assignment；
- 内部分配PARTID/PMG；
- task group优先于CPU default；
- 每资源domain保存独立schema。

证据来源必须先调研：

- Linux内核官方resctrl文档；
- Linux arm64 MPAM官方文档和上游源码；
- Arm官方MPAM架构资料；
- libvirt官方cachetune/memorytune接口。

验证：

- 软件组配置可以解析为现有settings table；
- PMG作用域不跨PARTID；
- 组迁移后新事务使用新标签，已发事务保持原标签；
- UI显示软件组和最终硬件标签映射。

### 步骤8：验证等级、watchdog和完整追踪

建议change：`add-validation-levels-and-watchdog`

目标：

- `basic`验证关键不变量；
- `full`记录victim、candidate、flit、comparator和因果证据；
- 非侵入式progress watchdog识别内部lost wakeup；
- 目标未达、饱和、振荡、过冲和控制导致无进展继续仿真。

停止条件只包括：

- 非法配置；
- 内部状态不变量破坏；
- 资源已释放但仲裁永不重新唤醒；
- 有限流量且endpoint ready时Ring停止移动；
- 事务丢失或重复完成。

### 步骤9：校准和实验模板

建议change：`add-calibration-and-experiment-templates`

目标：

- 为NoC、L3、MC延迟和带宽提供校准入口；
- 保存配置、seed、commit、组件版本和环境摘要；
- 提供no-control、单控制、组合控制和恢复实验模板；
- 输出overshoot area、queue area、恢复周期、公平性、P99/P999和饥饿证据。

绝对性能结论必须附RTL、FPGA、硅片或公开论文数据来源；没有校准时只报告
机制和趋势。

## 3. 每步统一执行模板

```bash
openspec new change <change-name>
openspec validate <change-name> --strict
PYTHONPATH=. python3 -m pytest <targeted-tests>
PYTHONPATH=. python3 -m pytest
node --check src/web/static/app.js
openspec validate --all --strict
```

浏览器验收：

1. 启动`python3 -m src.web.server --host 127.0.0.1 --port 8787`；
2. 修改本步骤新增参数；
3. 执行短仿真；
4. 检查目标、实际、raw、filtered、状态和事件；
5. 检查console error、布局重叠和tooltip完整性；
6. 完成tasks后归档OpenSpec；
7. 一个change对应一个可独立回归的git commit。

## 4. 禁止事项

- 不恢复token bucket作为默认BMIN/BMAX算法；
- 不恢复每PARTID FIFO队首候选；
- 不让NoC读取MC QoS或PARTID进行优先上下Ring；
- 不用完整physical L3 occupancy替代MPAM sampled/filtered控制输入；
- 不把“达到目标”写成所有控制测试的通过条件；
- 不在Web建立与YAML/Python不同的隐藏配置模型；
- 不在没有证据时声称某种策略是现有商业SoC的真实实现；
- 不用大规模重构替代当前模块化原位迁移。

## 5. 当前启动与验收

```bash
cd /Users/a1/Documents/Codex/2026-06-13/files-mentioned-by-the-user-soc/soc_flow_mpam_sim_project
PYTHONPATH=. python3 -m src.web.server --host 127.0.0.1 --port 8787
```

浏览器地址：`http://127.0.0.1:8787/`

当前页面可配置16线程、16个PARTID、CPU/Core OSTD、三Ring、真实L3、
L3/MC本地监控、CMIN/CMAX、BMIN/BMAX、MC QoS、CBusy和地址交织，
并直接运行仿真查看结果。
