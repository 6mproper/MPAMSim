const state = {
  defaults: {},
  jobId: null,
  experimentJobId: null,
  verificationJobId: null,
  polling: null,
  experimentPolling: null,
  verificationPolling: null,
  result: null,
  experiment: null,
  experimentPartial: null,
  verification: null,
  verificationPartial: null,
  presets: [],
  uiMetadata: {},
  partial: {
    metrics: [],
    cpu: [],
    cpu_mc: [],
    msc: [],
    controls: [],
    time_ns: 0,
  },
  selectedTime: 0,
  playing: false,
  playTimer: null,
  partidConfigs: [],
  stimulusConfigs: [],
  resctrlGroups: [],
  resourceView: "cpu",
  overviewPartid: 0,
  overviewChartLayers: {
    targetBand: true,
    controlInput: true,
    filtered: false,
    actual: true,
    raw: false,
    events: true,
  },
  advancedEvidenceView: "resource-monitor",
  causalPartid: 0,
  experimentPartid: 0,
  effectPartid: 0,
  visiblePartids: new Set(Array.from({ length: 16 }, (_, partid) => partid)),
};

const colors = {
  p1: "#1778aa",
  p2: "#d46b21",
  green: "#2d7a4c",
  amber: "#b76e00",
  grid: "#dce2e6",
  axis: "#697680",
};
const partidPalette = [
  "#1778aa", "#d46b21", "#2d7a4c", "#8064a2",
  "#b23a48", "#2b8c8c", "#a66a00", "#5f6f82",
  "#3f7cac", "#c0527c", "#6b8e23", "#8c5e3c",
  "#397367", "#7851a9", "#b05f36", "#4f6d7a",
];

const configHeaderFields = {
  stimulus: {
    Requester: "requester",
    En: "enabled",
    PARTID: "partid",
    PMG: "pmg",
    Type: "workload_type",
    Addr: "address_pattern",
    Dep: "dependency_mode",
    Issue: "issue_selection",
    SrcQ: "source_queue_depth",
    Rate: "rate_value",
    Unit: "rate_unit",
    Bytes: "request_size_bytes",
    Read: "read_ratio",
    "WSS MB": "working_set_mb",
    "Base MB": "address_base_mb",
    "P99 ns": "target_p99_ns",
  },
  partid: {
    PARTID: "partid",
    Name: "name",
    Mon: "monitor_enable",
    "CMIN %": "cmin",
    "CMAX %": "cmax",
    CPBM: "cpbm",
    BMIN: "bmin_gbps",
    BMAX: "bmax_gbps",
    Mode: "limit_mode",
    "MC QoS": "mc_qos",
    "CBusy / OSTD": "cbusy_enable",
  },
};
const headerHelp = {
  "PARTID / PMG": "软件可见监控 key。PARTID 选择控制策略，PMG 细分同一控制分区内的监控归因。",
  "L3 Sample BW": "该监控组在 L3 抽样 set 上观察到并按 8 倍估算的访问带宽。",
  "L3 Est. Occupancy": "该监控组在抽样 way 中的所有权按 8-set 分组放大的估算字节数。",
  "L3 Est / Actual": "1/8抽样set放大后的估算占用，与扫描全部真实valid line得到的实际占用。",
  "Monitor Error": "抽样估算占用减去实际占用；地址交织和有限抽样可使该值为正或负。",
  "MSHR": "全部L3实例当前/峰值/配置MSHR，以及等待分配MSHR的miss数量。",
  "Fill Buffer": "全部L3实例当前/峰值/配置fill entry；满时返回flit不能下Ring。",
  "Merge / Bypass": "同line read合并次数与因CPBM/CMIN/CMAX无合法victim而不写入L3的fill次数。",
  "L3 Occupancy %": "估算占用字节除以该 PARTID 当前允许的 L3 容量；这是近似 CSU，不是精确 tag-array 统计。",
  "MC BW": "该监控组在所有内存控制器上实际完成服务的带宽之和。",
  "Raw / Filtered BW": "MC每256个本地拍根据已服务字节得到raw带宽，再按history/current权重发布滤波MPAM监控值；控制读取该滤波值。",
  "Limit State": "上一已发布滤波监控值形成的UNDER_BMIN、OVER_BMAX和HARD_BLOCK锁存状态。",
  "Buffer / Candidate / Grant": "当前该PARTID占用的共享buffer entry，以及本导出周期参与全深度ready比较和获得授权的累计次数。",
  "MC BW Util %": "监控组 MC 带宽除以参与统计的 MC 总建模带宽。",
  "MC Requests": "最新采样周期内该监控组在 MC 完成调度的请求数。",
  "Throttle ns": "最新周期内 hard limit 等待累计时间。",
  "OSTD Current / Peak": "采样时刻当前 outstanding requests，以及该控制周期内观察到的峰值。",
  "Core Pool / ID OSTD": "该 PARTID 所在 Core 的共享池总占用/峰值/上限，以及 Core 内该 PARTID 的合计占用；共享池总占用包含其他 PARTID。",
  "Home MC ID OSTD": "按目标 MC 分开的 Core/PARTID outstanding、周期峰值、有效 CBusy cap 与等级；MC0 的反馈不限制发往 MC1 的请求。",
  "OSTD Util %": "当前 outstanding 除以该 PARTID 所关联 requester 的最大 outstanding 容量之和。",
  "Issued / Completed": "仿真开始以来该 PARTID 在 CPU requester 侧累计发出和完成的请求数。",
  "Backpressure ns": "requester 因 outstanding 达到上限而延迟发出的累计时间。",
  "CBusy": "所有 MC 对该 PARTID 反馈的最高 CBusy 档位及对应 effective OSTD。",
  "CBusy Stall ns": "因 CBusy-derived effective OSTD 达到上限而产生的源端累计等待。",
  "Offered / Injected": "端点希望发送的flit数，以及实际占用源link槽进入Ring的flit数。",
  "Ejected / Transfers": "成功下Ring的flit数，以及完成全部flit重组的transaction数。",
  "Failed / Full Laps": "目标端暂不可接收导致的失败下Ring次数，以及flit完成整圈绕行次数。",
  "Injection BP": "源link没有空槽导致的注入反压事件和累计等待时间。",
  "L3 Occupancy": "所有 L3 实例的 8-set 抽样占用估算之和。",
  "Physical / Raw / Control": "Physical来自全部真实set/tag/way；Raw来自当前采样offset的owner并按monitor group比例缩放；Control是CMIN/CMAX实际读取的已发布抽样占用。",
  "L3 Util %": "估算 L3 占用除以该 PARTID 在所有 L3 实例上的允许容量。",
  "Hit Rate": "最新采样周期内该 PARTID 在 L3 的概率命中率。",
  "Alloc Denials": "因 CPBM 或 CMAX 无可用 way 而拒绝抽样分配的次数。",
  "L3 Queue": "所有 L3 实例的平均等待 entries / 配置深度，以及采样周期内峰值。",
  "Queue Delay / Full": "该 PARTID 在 L3 FIFO 中累计等待时间，以及入口队列满导致的重试事件。",
  "MC Util %": "该 PARTID 在所有 MC 上的带宽之和除以这些 MC 的总建模带宽。",
  "Avg Queue ns": "最新采样周期内该 PARTID 在 MC 队列中的平均等待时间。",
  "Limit Events": "softlimit竞争降档次数、周期hard gate事件、被选中超限请求和QoS饱和证据。",
  "CBusy Evidence": "最高档位、带宽/BMAX 比、队列比、占空比和本周期切换次数。",
  "Control State": "当前策略状态，以及该 PARTID 最近一次闭环控制更新。",
  "PARTID": "资源控制聚合标识；同一 PARTID 下的多个 PMG 会合并到该行。",
  "吞吐 Gbps": "该 PARTID 在最新采样周期内完成字节换算的有效带宽。",
  "命中率": "该 PARTID 的概率 L3 命中请求占比。",
  "MC Queue ns": "该 PARTID 请求在内存控制器队列中的平均等待时间。",
  "MSC": "Memory System Component 标识，如 NoC、L3/SLC 或内存控制器。",
  "类型": "组件模型类型。",
  "利用率": "组件报告的总体利用率；不同 MSC 的分母语义不同。",
  "队列占用": "采样周期内组件队列的平均 entries。",
  "请求数": "采样周期内组件处理的请求数量。",
  "传输字节": "采样周期内组件处理的数据字节数。",
  "时间 ns": "控制更新发生的仿真时间。",
  "目标": "被写入控制值的 MSC。",
  "字段": "策略修改的设置字段。",
  "旧值": "控制更新前的值。",
  "新值": "控制更新后的值。",
  "原因": "策略触发此次更新的监控条件。",
  "L3 Sample BW Σ": "所有 L3 实例对该 PARTID 的 8-set 抽样带宽估算之和。",
  "L3 Est. Occupancy Σ": "所有 L3 实例对该 PARTID 的抽样占用估算之和。",
  "Ways Σ": "所有 L3 实例中该 PARTID 当前拥有的抽样 way 数之和。",
  "MC BW Σ": "所有内存控制器中该 PARTID 的实测带宽之和。",
  "BMIN Σ": "各 MC 独立 BMIN 配置的显示求和，不表示一个全局 token bucket。",
  "BMAX Σ": "各 MC 独立 BMAX 配置的显示求和，不表示一个全局 token bucket。",
  "QoS Base / Eff": "MC 配置的基础 3-bit QoS，以及本周期叠加 aging、BMIN 升档和 softlimit 降档后的请求加权平均值。",
  "Soft Req": "超出 soft BMAX 且发生竞争时被标记为低偏好的请求数。",
  "Hard Blocks": "上一周期滤波带宽触发hard BMAX后，整监控周期阻止该PARTID参与调度的事件数。",
};
const resultTabHelp = {
  "资源监控": "在 CPU、L3、MC 之间切换，并用同一组 PARTID 开关查看资源状态和控制反馈。",
  "控制效果": "同时显示配置目标、实际结果、适用条件与完整时间变化，用于判断控制是否真正生效。",
  "对照实验": "使用相同输入自动比较参考、BMAX-only、CBusy-only和组合控制的收益与代价。",
  "算法验证": "运行内置确定性微基准，分别验证 CMIN、CMAX、BMIN、BMAX softlimit 和 hardlimit 的模型算法。",
  "因果时间线": "按控制周期对齐MC压力、CBusy、effective OSTD、源端stall和业务性能。",
  "PARTID": "按 PARTID 聚合的吞吐、尾延迟、命中率和延迟分量。",
  "监控组": "按 PARTID+PMG 显示软件可见的实时 L3 占用和 MC 带宽使用。",
  "MPAM 监控": "按 PARTID 聚合所有 L3/MC 实例的控制值和限速事件。",
  "MSC": "显示 NoC、L3 和 MC 组件级利用率、队列和流量。",
  "控制记录": "显示闭环策略在各采样周期写入的控制更新。",
};
const sectionHeadingHelp = {
  "仿真与多核": "定义运行时间、采样周期以及 8 核 16 线程 requester 的公共约束。",
  "L3 / SLC": "定义共享缓存实例、几何、抽样监控粒度和固定查询延迟。",
  "NoC": "定义抽象互连的 router、链路、队列和虚通道容量。",
  "Memory Controller": "定义内存控制器数量、通道带宽、服务延迟和队列深度。",
  "16 线程独立激励": "为8核16线程分别配置标签、地址行为、速率、请求大小、读写比例、工作集和P99目标。",
  "16 PARTID Cache / Memory 控制": "每行配置一个 PARTID 的 L3 百分比、MC 带宽、3-bit QoS 和监控开关。",
  "控制模式": "选择是否执行 MPAM 控制，以及是否允许运行时闭环更新。",
  "闭环参数": "控制闭环的步长、滞回和最小保持时间，避免频繁震荡。",
  "MC 调度算法参数": "配置MC本地256拍监控、历史滤波、BMIN/BMAX滞回、共享buffer 3-bit QoS和可选PARTID service deficit。",
  "CBusy 快反馈": "配置 MC per-PARTID 四档拥塞检测、反馈传播和逐级恢复行为。",
  "resctrl-like 软件资源组": "使用公开resctrl风格的软件组入口配置资源策略；本阶段会翻译为内部PARTID/PMG和现有MPAM控制，不模拟完整Linux文件系统。",
};

const resctrlHelp = {
  enabled: "启用该CTRL_MON group。root总是有效；关闭非root组后，其tasks/cpus_list不参与映射。",
  name: "CTRL_MON group目录名。必须唯一，不能包含/；UI会显示它到内部PARTID的只读映射。",
  partid: "内部PARTID映射。真实系统由驱动分配，本模型允许显式选择以便方案对照；所有启用组必须唯一。",
  mode: "resctrl mode。本阶段支持shareable/exclusive标签记录，不实现pseudo-locking或严格硬件独占校验。",
  schemata: "软件可写schema。支持L3:<domain>=<cbm>和MB:<domain>=<Gbps>两类；domain 0值会作为未列出domain的默认值。",
  tasks: "显式任务列表，格式可用thread_01、cpu0.t1、1或1-3；优先级为tasks > cpus_list > root。",
  cpus: "逻辑CPU默认组，格式如0-3,8；本模型把16个硬件线程槽位当作逻辑CPU 0..15。",
  mb_limit_mode: "把MB schema转换为MC BMAX时采用softlimit或hardlimit。公开resctrl不直接暴露本模型的soft/hard实现细节，这里作为仿真开关保留。",
  mon_groups: "MON group列表，每行name|pmg|tasks|cpus。MON group只改变PMG，不改变PARTID；PMG作用域限定在父CTRL_MON group内。",
  remove: "删除该软件组行；root组不建议删除，若缺失构建器会自动补root。",
};

const supplementalAlgorithmHelp = {
  "l3-allocation": {
    title: "L3 sampled-owner 分配算法",
    body: "每 8 个 set 只观察第一个 set 的各 way owner。替换时先检查请求者的全局 sampled ownership 是否达到 CMAX；未达到时优先空 way，再选择全局占用高于其 CMIN 配额的 owner 中最老的 way。该方法验证控制趋势，不等同于逐 tag 精确硬件实现。",
  },
  "effect-view": {
    title: "如何识别控制效果",
    body: "CMIN 只在该 PARTID 有需求且 L3 存在竞争时判定；BMIN 只在有需求且 MC 竞争时判定。CMAX 与 hard BMAX 是上界检查，soft BMAX 超限借用不是违规。曲线同时给出目标、实际和控制事件，避免只看最终平均值。",
  },
};
let algorithmHelp = { ...supplementalAlgorithmHelp };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function fieldMetadata(group, key) {
  return state.uiMetadata?.fields?.[group]?.[key] || null;
}

function fieldAlgorithm(group, key) {
  return state.uiMetadata?.control_field_algorithms?.[group]?.[key] || "";
}

function formatFieldHelp(group, key, selectedOption = null) {
  const metadata = fieldMetadata(group, key);
  if (!metadata) return "";
  const lines = [
    metadata.title,
    `含义：${metadata.summary}`,
    `单位：${metadata.unit}`,
    `作用位置：${metadata.location}`,
    `模型影响：${metadata.effect}`,
    `约束/边界：${metadata.constraints}`,
    `示例：${metadata.example}`,
    `模型状态：${metadata.model_status}`,
  ];
  const options = state.uiMetadata?.options?.[key];
  if (options) {
    lines.push(
      "可选值：",
      ...Object.entries(options).map(
        ([value, description]) =>
          `${String(value) === String(selectedOption) ? "→" : "•"} ${value}：${description}`,
      ),
    );
  }
  return lines.join("\n");
}

function configHelpAttributes(group, key, selectedOption = null) {
  const help = formatFieldHelp(group, key, selectedOption);
  const algorithm = fieldAlgorithm(group, key);
  return [
    `data-config-group="${escapeHtml(group)}"`,
    `data-config-key="${escapeHtml(key)}"`,
    help ? `data-help="${escapeHtml(help)}"` : "",
    algorithm ? `data-algorithm="${escapeHtml(algorithm)}"` : "",
  ].filter(Boolean).join(" ");
}

function setConfigHelp(target, group, key, selectedOption = null) {
  if (!target) return;
  const help = formatFieldHelp(group, key, selectedOption);
  setHelp(target, help);
  target.dataset.configGroup = group;
  target.dataset.configKey = key;
  const algorithm = fieldAlgorithm(group, key);
  if (algorithm) target.dataset.algorithm = algorithm;
  else delete target.dataset.algorithm;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

function setStatus(status, message, progress = 0) {
  const badge = $("#statusBadge");
  badge.className = `status-badge ${status}`;
  badge.textContent = status === "running" ? "RUNNING" :
    status === "completed" ? "DONE" :
    status === "failed" ? "FAILED" : "READY";
  $("#runMessage").textContent = message;
  $("#progressBar").style.width = `${Math.max(0, Math.min(1, progress)) * 100}%`;
  const activeIndex = Math.min(5, Math.floor(progress * 6));
  $$(".flow-stage").forEach((node, index) => {
    node.classList.toggle("active", status === "running" && index === activeIndex);
    node.classList.toggle("complete", status === "completed" || index < activeIndex);
  });
}

function fillForm(values) {
  renderPartidConfig(
    values.partid_configs || state.defaults.partid_configs || [],
  );
  renderStimulusConfig(
    values.stimulus_configs || state.defaults.stimulus_configs || [],
  );
  renderResctrlConfig(
    values.resctrl_groups || state.defaults.resctrl_groups || [],
  );
  $$("[data-param]").forEach((input) => {
    const key = input.dataset.param;
    if (!(key in values)) return;
    if (input.type === "radio") input.checked = input.value === String(values[key]);
    else if (input.type === "checkbox") input.checked = Boolean(values[key]);
    else input.value = values[key];
  });
  clampDependentInputs();
  renderSocCapabilitySummaries();
}

function collectParameters() {
  const parameters = {};
  $$("[data-param]").forEach((input) => {
    if (input.type === "radio" && !input.checked) return;
    let value = input.value;
    if (input.type === "number") value = Number(value);
    if (input.type === "checkbox") value = input.checked;
    parameters[input.dataset.param] = value;
  });
  parameters.partid_configs = collectPartidConfigs();
  parameters.stimulus_configs = collectStimulusConfigs();
  parameters.resctrl_groups = collectResctrlGroups();
  return parameters;
}

function selectOptions(values, selected) {
  return values.map(([value, label]) =>
    `<option value="${escapeHtml(value)}" ${String(value) === String(selected) ? "selected" : ""}>${escapeHtml(label)}</option>`
  ).join("");
}

function partidColor(partid) {
  return partidPalette[Number(partid) % partidPalette.length];
}

function renderPartidConfig(rows) {
  state.partidConfigs = rows.map((row) => ({ ...row }));
  $("#partidConfigTable").innerHTML = state.partidConfigs.map((row) => `
    <tr data-partid-row="${row.partid}">
      <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
      <td><input data-field="name" ${configHelpAttributes("partid", "name")} type="text" value="${escapeHtml(row.name)}" spellcheck="false"></td>
      <td><input data-field="monitor_enable" ${configHelpAttributes("partid", "monitor_enable")} type="checkbox" ${row.monitor_enable ? "checked" : ""}></td>
      <td>${controlField("cmin_enable", row.cmin_enable, "cmin", row.cmin, 'type="number" min="0" max="100" step="0.1"')}</td>
      <td>${controlField("cmax_enable", row.cmax_enable, "cmax", row.cmax, 'type="number" min="0" max="100" step="0.1"')}</td>
      <td>${controlField("cpbm_enable", row.cpbm_enable, "cpbm", row.cpbm, 'type="text" spellcheck="false"')}</td>
      <td>${controlField("bmin_enable", row.bmin_enable, "bmin_gbps", row.bmin_gbps, 'type="number" min="0" max="4096" step="1"')}</td>
      <td>${controlField("bmax_enable", row.bmax_enable, "bmax_gbps", row.bmax_gbps, 'type="number" min="0" max="4096" step="1"')}</td>
      <td><select data-field="limit_mode" ${configHelpAttributes("partid", "limit_mode", row.limit_mode)}>
        <option value="softlimit" ${row.limit_mode === "softlimit" ? "selected" : ""}>soft</option>
        <option value="hardlimit" ${row.limit_mode === "hardlimit" ? "selected" : ""}>hard</option>
      </select></td>
      <td>${controlField("mc_qos_enable", row.mc_qos_enable, "mc_qos", row.mc_qos, 'type="number" min="0" max="7" step="1"')}</td>
      <td>
        <div class="cbusy-control">
          <input data-field="cbusy_enable" ${configHelpAttributes("partid", "cbusy_enable")} type="checkbox" ${row.cbusy_enable ? "checked" : ""}>
          <div>
            <input data-field="cbusy_l1_ostd" ${configHelpAttributes("partid", "cbusy_l1_ostd")} type="number" min="1" max="1024" step="1" value="${row.cbusy_l1_ostd}">
            <input data-field="cbusy_l2_ostd" ${configHelpAttributes("partid", "cbusy_l2_ostd")} type="number" min="1" max="1024" step="1" value="${row.cbusy_l2_ostd}">
            <input data-field="cbusy_l3_ostd" ${configHelpAttributes("partid", "cbusy_l3_ostd")} type="number" min="1" max="1024" step="1" value="${row.cbusy_l3_ostd}">
          </div>
        </div>
      </td>
    </tr>
  `).join("");
}

function controlField(enableField, enabled, valueField, value, attributes) {
  return `
    <div class="control-field">
      <input data-field="${enableField}" ${configHelpAttributes("partid", enableField)} type="checkbox" ${enabled ? "checked" : ""}>
      <input data-field="${valueField}" ${configHelpAttributes("partid", valueField)} ${attributes} value="${escapeHtml(value)}">
    </div>`;
}

function collectPartidConfigs() {
  return $$("[data-partid-row]").map((row) => {
    const value = (field) => row.querySelector(`[data-field="${field}"]`);
    return {
      partid: Number(row.dataset.partidRow),
      name: value("name").value,
      monitor_enable: value("monitor_enable").checked,
      cpbm_enable: value("cpbm_enable").checked,
      cmin_enable: value("cmin_enable").checked,
      cmax_enable: value("cmax_enable").checked,
      cmin: Number(value("cmin").value),
      cmax: Number(value("cmax").value),
      cpbm: value("cpbm").value,
      bmin_enable: value("bmin_enable").checked,
      bmax_enable: value("bmax_enable").checked,
      bmin_gbps: Number(value("bmin_gbps").value),
      bmax_gbps: Number(value("bmax_gbps").value),
      limit_mode: value("limit_mode").value,
      mc_qos_enable: value("mc_qos_enable").checked,
      mc_qos: Number(value("mc_qos").value),
      cbusy_enable: value("cbusy_enable").checked,
      cbusy_l1_ostd: Number(value("cbusy_l1_ostd").value),
      cbusy_l2_ostd: Number(value("cbusy_l2_ostd").value),
      cbusy_l3_ostd: Number(value("cbusy_l3_ostd").value),
    };
  });
}

function renderStimulusConfig(rows) {
  state.stimulusConfigs = rows.map((row) => ({ ...row }));
  const partidOptions = Array.from(
    { length: 16 },
    (_, partid) => [partid, `PARTID ${partid}`],
  );
  const typeOptions = [
    ["stream", "stream"],
    ["pointer_chase", "pointer"],
    ["random_read", "random"],
    ["mixed_rw", "mixed"],
    ["bursty_dma", "burst"],
  ];
  const addressOptions = [
    ["sequential", "seq"],
    ["uniform_random", "rand"],
    ["pointer_chase", "ptr"],
    ["stride", "stride"],
    ["hotset", "hot"],
  ];
  const dependencyOptions = [
    ["independent", "indep"],
    ["pointer_chain", "chain"],
  ];
  const issueOptions = [
    ["fifo", "fifo"],
    ["eligible_scan", "scan"],
  ];
  $("#stimulusConfigTable").innerHTML = state.stimulusConfigs.map((row) => `
    <tr data-stimulus-row="${row.slot}">
      <td><span class="thread-chip">${escapeHtml(row.requester)}</span></td>
      <td><input data-stimulus-field="enabled" ${configHelpAttributes("stimulus", "enabled")} type="checkbox" ${row.enabled ? "checked" : ""}></td>
      <td><select data-stimulus-field="partid" ${configHelpAttributes("stimulus", "partid", row.partid)}>${selectOptions(partidOptions, row.partid)}</select></td>
      <td><input data-stimulus-field="pmg" ${configHelpAttributes("stimulus", "pmg")} type="number" min="0" max="15" step="1" value="${row.pmg}"></td>
      <td><select data-stimulus-field="workload_type" ${configHelpAttributes("stimulus", "workload_type", row.workload_type)}>${selectOptions(typeOptions, row.workload_type)}</select></td>
      <td><select data-stimulus-field="address_pattern" ${configHelpAttributes("stimulus", "address_pattern", row.address_pattern)}>${selectOptions(addressOptions, row.address_pattern || "sequential")}</select></td>
      <td><select data-stimulus-field="dependency_mode" ${configHelpAttributes("stimulus", "dependency_mode", row.dependency_mode)}>${selectOptions(dependencyOptions, row.dependency_mode || "independent")}</select></td>
      <td><select data-stimulus-field="issue_selection" ${configHelpAttributes("stimulus", "issue_selection", row.issue_selection)}>${selectOptions(issueOptions, row.issue_selection || "fifo")}</select></td>
      <td><input data-stimulus-field="source_queue_depth" ${configHelpAttributes("stimulus", "source_queue_depth")} type="number" min="1" max="4096" step="1" value="${row.source_queue_depth || 1}"></td>
      <td><input data-stimulus-field="rate_value" ${configHelpAttributes("stimulus", "rate_value")} type="number" min="0" max="4096" step="0.1" value="${row.rate_value}"></td>
      <td><select data-stimulus-field="rate_unit" ${configHelpAttributes("stimulus", "rate_unit", row.rate_unit)}>${selectOptions([["gbps", "Gbps"], ["mrps", "MRPS"]], row.rate_unit)}</select></td>
      <td><input data-stimulus-field="request_size_bytes" ${configHelpAttributes("stimulus", "request_size_bytes")} type="number" min="16" max="4096" step="16" value="${row.request_size_bytes}"></td>
      <td><input data-stimulus-field="read_ratio" ${configHelpAttributes("stimulus", "read_ratio")} type="number" min="0" max="1" step="0.05" value="${row.read_ratio}"></td>
      <td><input data-stimulus-field="working_set_mb" ${configHelpAttributes("stimulus", "working_set_mb")} type="number" min="1" max="262144" step="1" value="${row.working_set_mb}"></td>
      <td><input data-stimulus-field="address_base_mb" ${configHelpAttributes("stimulus", "address_base_mb")} type="number" min="0" max="1048576" step="1" value="${row.address_base_mb || 0}"></td>
      <td><input data-stimulus-field="target_p99_ns" ${configHelpAttributes("stimulus", "target_p99_ns")} type="number" min="0" max="1000000" step="1" value="${row.target_p99_ns}"></td>
    </tr>
  `).join("");
}

function collectStimulusConfigs() {
  return $$("[data-stimulus-row]").map((row) => {
    const value = (field) => row.querySelector(`[data-stimulus-field="${field}"]`);
    const slot = Number(row.dataset.stimulusRow);
    return {
      slot,
      enabled: value("enabled").checked,
      requester: `cpu${Math.floor(slot / 2)}.t${slot % 2}`,
      partid: Number(value("partid").value),
      pmg: Number(value("pmg").value),
      workload_type: value("workload_type").value,
      address_pattern: value("address_pattern").value,
      dependency_mode: value("dependency_mode").value,
      issue_selection: value("issue_selection").value,
      source_queue_depth: Number(value("source_queue_depth").value),
      eligible_scan_depth: Number(value("source_queue_depth").value),
      rate_value: Number(value("rate_value").value),
      rate_unit: value("rate_unit").value,
      request_size_bytes: Number(value("request_size_bytes").value),
      read_ratio: Number(value("read_ratio").value),
      working_set_mb: Number(value("working_set_mb").value),
      address_base_mb: Number(value("address_base_mb").value),
      target_p99_ns: Number(value("target_p99_ns").value),
    };
  });
}

function resctrlHelpAttr(key) {
  return `data-help="${escapeHtml(resctrlHelp[key] || "")}"`;
}

function monGroupsToText(value) {
  if (Array.isArray(value)) {
    return value.map((row) => [
      row.name || "",
      row.pmg ?? "",
      row.tasks || "",
      row.cpus || "",
    ].join("|")).join("\n");
  }
  return String(value || "");
}

function renderResctrlConfig(rows) {
  state.resctrlGroups = (rows || []).map((row) => ({ ...row }));
  $("#resctrlGroupTable").innerHTML = state.resctrlGroups.map((row, index) => `
    <tr data-resctrl-row="${index}">
      <td><input data-resctrl-field="enabled" ${resctrlHelpAttr("enabled")} type="checkbox" ${row.enabled !== false ? "checked" : ""}></td>
      <td><input data-resctrl-field="name" ${resctrlHelpAttr("name")} type="text" value="${escapeHtml(row.name || `group${index}`)}" spellcheck="false"></td>
      <td><input data-resctrl-field="partid" ${resctrlHelpAttr("partid")} type="number" min="0" max="15" step="1" value="${Number(row.partid ?? index)}"></td>
      <td><select data-resctrl-field="mode" ${resctrlHelpAttr("mode")}>
        ${selectOptions([["shareable", "shareable"], ["exclusive", "exclusive"]], row.mode || "shareable")}
      </select></td>
      <td><textarea data-resctrl-field="schemata" ${resctrlHelpAttr("schemata")} spellcheck="false">${escapeHtml(row.schemata || "")}</textarea></td>
      <td><input data-resctrl-field="tasks" ${resctrlHelpAttr("tasks")} type="text" value="${escapeHtml(row.tasks || "")}" spellcheck="false"></td>
      <td><input data-resctrl-field="cpus" ${resctrlHelpAttr("cpus")} type="text" value="${escapeHtml(row.cpus || "")}" spellcheck="false"></td>
      <td><select data-resctrl-field="mb_limit_mode" ${resctrlHelpAttr("mb_limit_mode")}>
        ${selectOptions([["softlimit", "soft"], ["hardlimit", "hard"]], row.mb_limit_mode || "softlimit")}
      </select></td>
      <td><textarea data-resctrl-field="mon_groups" ${resctrlHelpAttr("mon_groups")} spellcheck="false">${escapeHtml(monGroupsToText(row.mon_groups))}</textarea></td>
      <td><button type="button" class="resctrl-remove" data-remove-resctrl="${index}" ${resctrlHelpAttr("remove")}>×</button></td>
    </tr>
  `).join("");
}

function collectResctrlGroups() {
  return $$("[data-resctrl-row]").map((row) => {
    const value = (field) => row.querySelector(`[data-resctrl-field="${field}"]`);
    return {
      enabled: value("enabled").checked,
      name: value("name").value.trim(),
      partid: Number(value("partid").value),
      mode: value("mode").value,
      schemata: value("schemata").value,
      tasks: value("tasks").value,
      cpus: value("cpus").value,
      mb_limit_mode: value("mb_limit_mode").value,
      mon_groups: value("mon_groups").value,
    };
  });
}

function addResctrlGroup() {
  const groups = collectResctrlGroups();
  const used = new Set(groups.map((row) => Number(row.partid)));
  const partid = Array.from({ length: 16 }, (_, index) => index)
    .find((index) => !used.has(index)) ?? 15;
  groups.push({
    enabled: true,
    name: `group${partid}`,
    partid,
    mode: "shareable",
    schemata: "L3:0=ffff\nMB:0=256",
    tasks: "",
    cpus: "",
    mb_limit_mode: "softlimit",
    mon_groups: "",
  });
  renderResctrlConfig(groups);
  applyContextHelp();
  renderConfigDiagnostics();
}

function parseSlotSet(text, allowCpuName = true) {
  const result = new Set();
  String(text || "").split(/[;,]/).forEach((rawToken) => {
    const token = rawToken.trim();
    if (!token) return;
    const add = (slot) => {
      const value = Number(slot);
      if (Number.isInteger(value) && value >= 0 && value <= 15) {
        result.add(value);
      }
    };
    if (/^\d+-\d+$/.test(token)) {
      const [left, right] = token.split("-").map(Number);
      for (let value = left; value <= right; value += 1) add(value);
    } else if (/^thread_?\d+$/i.test(token)) {
      add(token.replace(/^thread_?/i, ""));
    } else if (allowCpuName && /^cpu\d+\.t\d+$/i.test(token)) {
      const [, core, thread] = token.match(/^cpu(\d+)\.t(\d+)$/i);
      add(Number(core) * 2 + Number(thread));
    } else {
      add(token);
    }
  });
  return result;
}

function parseMonGroupLines(text) {
  return String(text || "").split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const parts = line.split("|").map((part) => part.trim());
      return {
        name: parts[0] || `mon${index + 1}`,
        pmg: Number(parts[1] || index + 1),
        taskSlots: parseSlotSet(parts[2] || ""),
        cpuSlots: parseSlotSet(parts[3] || "", false),
      };
    });
}

function resctrlAssignments() {
  const groups = collectResctrlGroups()
    .filter((row) => row.enabled || row.name === "root");
  const root = groups.find((row) => row.name === "root") || groups[0] || {
    name: "root",
    partid: 0,
    mon_groups: "",
  };
  const taskGroups = new Map();
  const cpuGroups = new Map();
  groups.forEach((group) => {
    parseSlotSet(group.tasks).forEach((slot) => taskGroups.set(slot, group));
    if (group.name !== "root") {
      parseSlotSet(group.cpus, false).forEach((slot) => cpuGroups.set(slot, group));
    }
  });
  const bySlot = new Map();
  Array.from({ length: 16 }, (_, slot) => slot).forEach((slot) => {
    const group = taskGroups.get(slot) || cpuGroups.get(slot) || root;
    const monGroup = parseMonGroupLines(group.mon_groups).find((row) =>
      row.taskSlots.has(slot) || row.cpuSlots.has(slot)
    );
    bySlot.set(slot, {
      slot,
      group,
      partid: Number(group.partid || 0),
      pmg: monGroup ? Number(monGroup.pmg || 0) : 0,
      monGroup: monGroup?.name || "",
    });
  });
  return bySlot;
}

function normalizePartidMasks() {
  const ways = Number($('[data-param="l3_ways"]').value || 1);
  const maximum = (1n << BigInt(ways)) - 1n;
  const width = Math.max(1, Math.ceil(ways / 4));
  $$("[data-partid-row]").forEach((row) => {
    const cpbm = row.querySelector('[data-field="cpbm"]');
    let parsed;
    try {
      parsed = BigInt(`0x${cpbm.value.replace(/^0x/i, "") || "0"}`);
    } catch {
      parsed = maximum;
    }
    parsed &= maximum;
    cpbm.value = parsed.toString(16).padStart(width, "0");
    const cmax = row.querySelector('[data-field="cmax"]');
    const cmin = row.querySelector('[data-field="cmin"]');
    cmax.max = 100;
    cmin.max = 100;
    cmax.value = Math.min(Number(cmax.value), 100);
    cmin.value = Math.min(Number(cmin.value), Number(cmax.value));
  });
}

function clampDependentInputs() {
  const cores = Number($('[data-param="active_cores"]').value || 8);
  const l3 = $('[data-param="l3_instances"]');
  l3.max = Math.min(8, cores);
  if (Number(l3.value) > Number(l3.max)) l3.value = l3.max;
  const interval = $('[data-param="control_interval_ns"]');
  interval.max = $('[data-param="duration_ns"]').value;
  if (Number(interval.value) > Number(interval.max)) interval.value = interval.max;
  normalizePartidMasks();
  normalizeCbusyCaps();
}

function normalizeCbusyCaps() {
  const configuredMax = Number(
    $('[data-param="max_outstanding"]').value || 1
  );
  $$("[data-partid-row]").forEach((row) => {
    const l1 = row.querySelector('[data-field="cbusy_l1_ostd"]');
    const l2 = row.querySelector('[data-field="cbusy_l2_ostd"]');
    const l3 = row.querySelector('[data-field="cbusy_l3_ostd"]');
    l1.max = configuredMax;
    l1.value = Math.max(1, Math.min(configuredMax, Number(l1.value)));
    l2.max = l1.value;
    l2.value = Math.max(1, Math.min(Number(l1.value), Number(l2.value)));
    l3.max = l2.value;
    l3.value = Math.max(1, Math.min(Number(l2.value), Number(l3.value)));
  });
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => toast.classList.remove("visible"), 5000);
}

function presetById(id) {
  return state.presets.find((preset) => preset.id === id) || null;
}

function activePartidsFromParameters(parameters) {
  return [...new Set(
    (parameters.stimulus_configs || [])
      .filter((row) => row.enabled)
      .map((row) => Number(row.partid))
      .filter((partid) => Number.isFinite(partid)),
  )].sort((left, right) => left - right);
}

function updatePresetSummary() {
  const output = $("#presetExpected");
  if (!output) return;
  const preset = presetById($("#presetSelect")?.value || "");
  if (!preset) {
    output.textContent = "选择预设后查看预期观察点。";
    return;
  }
  output.innerHTML = `
    <b>${escapeHtml(preset.summary)}</b>
    <span>${escapeHtml(preset.expected)}</span>
  `;
}

function renderPresetSelector() {
  const select = $("#presetSelect");
  if (!select) return;
  select.innerHTML = [
    '<option value="">默认初始配置</option>',
    ...state.presets.map((preset) =>
      `<option value="${escapeHtml(preset.id)}">${escapeHtml(preset.name)}</option>`
    ),
  ].join("");
  updatePresetSummary();
}

function focusPresetPartids(parameters) {
  const activePartids = activePartidsFromParameters(parameters);
  if (!activePartids.length) return;
  const first = activePartids[0];
  state.visiblePartids = new Set(activePartids);
  state.overviewPartid = first;
  state.effectPartid = first;
  state.causalPartid = first;
  state.experimentPartid = first;
}

function applySelectedPreset() {
  const preset = presetById($("#presetSelect")?.value || "");
  if (!preset) {
    fillForm(state.defaults);
    state.visiblePartids = new Set(
      Array.from({ length: 16 }, (_, partid) => partid),
    );
    state.overviewPartid = 0;
    state.effectPartid = 0;
    state.causalPartid = 0;
    state.experimentPartid = 0;
    applyContextHelp();
    renderConfigDiagnostics();
    setStatus("ready", "已恢复默认初始配置", 0);
    renderAll();
    showToast("已恢复默认初始配置");
    return;
  }
  const parameters = JSON.parse(JSON.stringify(preset.parameters));
  fillForm(parameters);
  focusPresetPartids(parameters);
  applyContextHelp();
  renderConfigDiagnostics();
  setStatus("ready", `已应用预设：${preset.name}`, 0);
  renderAll();
  showToast(`已应用预设：${preset.name}`);
}

async function loadDefaults() {
  const payload = await requestJson("/api/defaults");
  state.uiMetadata = payload.ui_metadata || {};
  algorithmHelp = {
    ...supplementalAlgorithmHelp,
    ...(state.uiMetadata.control_algorithms || {}),
  };
  state.defaults = payload.parameters;
  state.presets = payload.presets || [];
  renderPresetSelector();
  fillForm(state.defaults);
}

async function runSimulation() {
  stopPlayback();
  clearTimeout(state.polling);
  state.partidConfigs = collectPartidConfigs();
  state.stimulusConfigs = collectStimulusConfigs();
  state.result = null;
  state.partial = {
    metrics: [],
    cpu: [],
    cpu_mc: [],
    msc: [],
    controls: [],
    time_ns: 0,
  };
  state.selectedTime = 0;
  $("#runButton").disabled = true;
  $("#experimentButton").disabled = true;
  $("#controlVerificationButton").disabled = true;
  $("#reportLink").classList.add("disabled");
  $("#reportLink").href = "#";
  setStatus("running", "提交仿真配置", 0.01);
  renderAll();
  try {
    const payload = await requestJson("/api/jobs", {
      method: "POST",
      body: JSON.stringify({ parameters: collectParameters() }),
    });
    state.jobId = payload.job_id;
    pollJob();
  } catch (error) {
    failRun(error.message);
  }
}

async function runExperiment() {
  clearTimeout(state.experimentPolling);
  state.partidConfigs = collectPartidConfigs();
  state.stimulusConfigs = collectStimulusConfigs();
  state.experiment = null;
  state.experimentPartial = null;
  $("#experimentButton").disabled = true;
  $("#runButton").disabled = true;
  $("#controlVerificationButton").disabled = true;
  setStatus("running", "准备四组对照实验", 0.01);
  activateResultTab("experiment");
  renderExperiment();
  try {
    const payload = await requestJson("/api/experiments", {
      method: "POST",
      body: JSON.stringify({ parameters: collectParameters() }),
    });
    state.experimentJobId = payload.job_id;
    pollExperiment();
  } catch (error) {
    failExperiment(error.message);
  }
}

async function pollExperiment() {
  try {
    const job = await requestJson(
      `/api/experiments/${state.experimentJobId}`,
    );
    state.experimentPartial = job.partial || state.experimentPartial;
    setStatus(
      job.status === "completed" ? "completed" :
        job.status === "failed" ? "failed" : "running",
      job.message,
      job.progress,
    );
    renderExperiment();
    if (job.status === "completed") {
      state.experiment = job.result;
      $("#experimentButton").disabled = false;
      $("#runButton").disabled = false;
      $("#controlVerificationButton").disabled = false;
      setStatus("completed", "四组机制对照完成", 1);
      renderExperiment();
      return;
    }
    if (job.status === "failed") {
      failExperiment(job.error || "对照实验失败");
      return;
    }
    state.experimentPolling = setTimeout(pollExperiment, 300);
  } catch (error) {
    failExperiment(error.message);
  }
}

function failExperiment(message) {
  clearTimeout(state.experimentPolling);
  $("#experimentButton").disabled = false;
  $("#runButton").disabled = false;
  $("#controlVerificationButton").disabled = false;
  setStatus("failed", "对照实验失败", 0);
  showToast(message);
}

async function runControlVerification() {
  clearTimeout(state.verificationPolling);
  state.verification = null;
  state.verificationPartial = null;
  $("#controlVerificationButton").disabled = true;
  $("#experimentButton").disabled = true;
  $("#runButton").disabled = true;
  setStatus("running", "准备控制算法验证", 0.01);
  activateResultTab("verification");
  renderControlVerification();
  try {
    const payload = await requestJson("/api/verifications", {
      method: "POST",
      body: JSON.stringify({ parameters: collectParameters() }),
    });
    state.verificationJobId = payload.job_id;
    pollControlVerification();
  } catch (error) {
    failControlVerification(error.message);
  }
}

async function pollControlVerification() {
  try {
    const job = await requestJson(
      `/api/verifications/${state.verificationJobId}`,
    );
    state.verificationPartial = job.partial || state.verificationPartial;
    setStatus(
      job.status === "completed" ? "completed" :
        job.status === "failed" ? "failed" : "running",
      job.message,
      job.progress,
    );
    renderControlVerification();
    if (job.status === "completed") {
      state.verification = job.result;
      $("#controlVerificationButton").disabled = false;
      $("#experimentButton").disabled = false;
      $("#runButton").disabled = false;
      setStatus(
        "completed",
        `控制算法验证 ${job.result.passed}/${job.result.total}`,
        1,
      );
      renderControlVerification();
      return;
    }
    if (job.status === "failed") {
      failControlVerification(job.error || "控制算法验证失败");
      return;
    }
    state.verificationPolling = setTimeout(
      pollControlVerification,
      300,
    );
  } catch (error) {
    failControlVerification(error.message);
  }
}

function failControlVerification(message) {
  clearTimeout(state.verificationPolling);
  $("#controlVerificationButton").disabled = false;
  $("#experimentButton").disabled = false;
  $("#runButton").disabled = false;
  setStatus("failed", "控制算法验证失败", 0);
  showToast(message);
}

async function pollJob() {
  try {
    const job = await requestJson(`/api/jobs/${state.jobId}`);
    state.partial = job.partial || state.partial;
    setStatus(
      job.status === "completed" ? "completed" :
        job.status === "failed" ? "failed" : "running",
      job.message,
      job.progress,
    );
    if (state.partial.time_ns) {
      state.selectedTime = state.partial.time_ns;
      syncTimeline();
      renderAll();
    }
    if (job.status === "completed") {
      state.result = job.result;
      state.partial = {
        metrics: job.result.metrics,
        cpu: job.result.cpu,
        cpu_mc: job.result.cpu_mc,
        msc: job.result.msc,
        controls: job.result.controls,
        time_ns: job.result.summary.simulation_time_ns,
      };
      state.selectedTime = state.partial.time_ns;
      $("#runButton").disabled = false;
      $("#experimentButton").disabled = false;
      $("#controlVerificationButton").disabled = false;
      $("#reportLink").href = job.result.report_url;
      $("#reportLink").classList.remove("disabled");
      syncTimeline();
      renderAll();
      return;
    }
    if (job.status === "failed") {
      failRun(job.error || "仿真失败");
      return;
    }
    state.polling = setTimeout(pollJob, 220);
  } catch (error) {
    failRun(error.message);
  }
}

function failRun(message) {
  clearTimeout(state.polling);
  $("#runButton").disabled = false;
  $("#experimentButton").disabled = false;
  $("#controlVerificationButton").disabled = false;
  setStatus("failed", "仿真失败", 0);
  showToast(message);
}

function activateResultTab(name) {
  $$(".result-tab").forEach((node) => {
    node.classList.toggle("active", node.dataset.resultTab === name);
  });
  $$(".result-view").forEach((view) => {
    view.classList.toggle("active", view.dataset.resultView === name);
  });
}

function syncTimeline() {
  const maxTime = Number(state.result?.summary.simulation_time_ns || state.partial.time_ns || 0);
  const slider = $("#timeSlider");
  slider.max = Math.max(1, maxTime);
  slider.value = Math.min(maxTime, state.selectedTime || maxTime);
  $("#timeOutput").textContent = formatTime(Number(slider.value));
}

function formatTime(value) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)} ms`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)} µs`;
  return `${Math.round(value)} ns`;
}

function formatNumber(value, digits = 1) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  if (Math.abs(number) >= 1_000_000) return `${(number / 1_000_000).toFixed(digits)}M`;
  if (Math.abs(number) >= 1_000) return `${(number / 1_000).toFixed(digits)}k`;
  return number.toFixed(digits);
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes <= 0) return "--";
  const units = ["B", "KiB", "MiB", "GiB"];
  let scaled = bytes;
  let unit = units[0];
  for (let index = 1; index < units.length && scaled >= 1024; index += 1) {
    scaled /= 1024;
    unit = units[index];
  }
  return `${formatNumber(scaled, scaled < 10 ? 2 : 1)} ${unit}`;
}

function numberParam(name, fallback = 0) {
  const value = Number($(`[data-param="${name}"]`)?.value);
  return Number.isFinite(value) ? value : fallback;
}

function setCapabilityRow(selector, title, detail) {
  const target = $(selector);
  if (!target) return;
  target.innerHTML = `
    <b>${escapeHtml(title)}</b>
    <span>${escapeHtml(detail)}</span>
  `;
}

function stimulusOfferedBandwidthGbps() {
  return collectStimulusConfigs()
    .filter((row) => row.enabled)
    .reduce((sum, row) => {
      const rate = Number(row.rate_value || 0);
      const bytes = Number(row.request_size_bytes || 64);
      if (String(row.rate_unit).toLowerCase() === "mrps") {
        return sum + rate * bytes * 0.008;
      }
      return sum + rate;
    }, 0);
}

function renderSocCapabilitySummaries() {
  if (!$("#socCpuCapability")) return;
  const activeCores = numberParam("active_cores", 8);
  const threadsPerCore = numberParam("threads_per_core", 2);
  const hardwareThreads = activeCores * threadsPerCore;
  const enabledStimuli = collectStimulusConfigs()
    .filter((row) => row.enabled)
    .length;
  const threadOstd = numberParam("max_outstanding", 32);
  const coreOstd = numberParam("core_max_outstanding", 48);
  const threadTotal = hardwareThreads * threadOstd;
  const coreTotal = activeCores * coreOstd;
  const effectiveOstd = Math.min(threadTotal, coreTotal);
  setCapabilityRow(
    "#socCpuCapability",
    `源端 offered ${formatNumber(stimulusOfferedBandwidthGbps(), 1)} Gbps`,
    `${enabledStimuli}/${hardwareThreads}路激励 · OSTD聚合上限 ${formatNumber(effectiveOstd, 0)} req（thread ${formatNumber(threadTotal, 0)} / core pool ${formatNumber(coreTotal, 0)}）`,
  );

  const l3Instances = numberParam("l3_instances", 1);
  const l3Sets = numberParam("l3_sets", 1);
  const l3Ways = numberParam("l3_ways", 1);
  const lineBytes = numberParam("l3_line_size", 64);
  const lookupParallelism = numberParam("l3_lookup_parallelism", 1);
  const hitLatency = Math.max(1e-9, numberParam("l3_hit_latency_ns", 1));
  const l3Clock = Math.max(1e-9, numberParam("l3_clock_mhz", 1000));
  const l3MonitorCycles = numberParam("l3_monitor_period_cycles", 256);
  const l3CapacityBytes = l3Instances * l3Sets * l3Ways * lineBytes;
  const l3LookupGbps = l3Instances * lookupParallelism * lineBytes * 8 / hitLatency;
  const l3MonitorNs = l3MonitorCycles * 1000 / l3Clock;
  setCapabilityRow(
    "#socL3Capability",
    `L3容量 ${formatBytes(l3CapacityBytes)} · lookup峰值 ${formatNumber(l3LookupGbps, 1)} Gbps`,
    `${l3Instances}实例 × ${formatNumber(lookupParallelism, 0)}槽 · line ${formatNumber(lineBytes, 0)}B · monitor ${formatNumber(l3MonitorNs, 2)} ns`,
  );

  const nocRouters = numberParam("noc_routers", 1);
  const mcCount = numberParam("memory_controllers", 1);
  const nocNodes = nocRouters + l3Instances + mcCount;
  const nocClock = Math.max(1e-9, numberParam("noc_clock_mhz", 1000));
  const nocHopCycles = numberParam("noc_hop_latency_cycles", 1);
  const nocSlots = numberParam("noc_link_slots_per_direction", 1);
  const flitBytes = numberParam("noc_flit_bytes", 16);
  const hopNs = nocHopCycles * 1000 / nocClock;
  const perLinkGbps = 3 * 2 * nocSlots * flitBytes * 8 / Math.max(1e-9, hopNs);
  const ringAggregateGbps = perLinkGbps * nocNodes;
  setCapabilityRow(
    "#socNocCapability",
    `Ring DAT等效聚合 ${formatNumber(ringAggregateGbps, 1)} Gbps`,
    `${nocNodes}节点 · 单link双向三通道 ${formatNumber(perLinkGbps, 1)} Gbps · hop ${formatNumber(hopNs, 2)} ns`,
  );

  const channelsPerMc = numberParam("channels_per_mc", 1);
  const channelBandwidth = numberParam("channel_bandwidth_gbps", 1);
  const mcClock = Math.max(1e-9, numberParam("mc_clock_mhz", 1000));
  const mcMonitorCycles = numberParam("mc_monitor_period_cycles", 256);
  const perMcGbps = channelsPerMc * channelBandwidth;
  const totalMcGbps = mcCount * perMcGbps;
  const mcMonitorNs = mcMonitorCycles * 1000 / mcClock;
  setCapabilityRow(
    "#socMcCapability",
    `MC系统带宽 ${formatNumber(totalMcGbps, 1)} Gbps`,
    `${mcCount} MC × ${channelsPerMc}通道 × ${formatNumber(channelBandwidth, 1)} Gbps · 每MC ${formatNumber(perMcGbps, 1)} Gbps · monitor ${formatNumber(mcMonitorNs, 2)} ns`,
  );
}

function visibleRows(rows) {
  return (rows || []).filter((row) => Number(row.time_ns || 0) <= state.selectedTime + 1e-9);
}

function latestBy(rows, key) {
  const result = new Map();
  visibleRows(rows).forEach((row) => result.set(String(row[key]), row));
  return [...result.values()];
}

function latestByKeys(rows, keys) {
  const result = new Map();
  visibleRows(rows).forEach((row) => {
    result.set(keys.map((key) => String(row[key])).join(":"), row);
  });
  return [...result.values()];
}

function isPartidVisible(partid) {
  return state.visiblePartids.has(Number(partid));
}

function renderPartidVisibility() {
  $("#partidVisibility").innerHTML = Array.from({ length: 16 }, (_, partid) => `
    <label class="partid-visibility-toggle" data-partid-toggle="${partid}" style="--partid-color:${partidColor(partid)}" data-help="切换 PARTID ${partid} 在资源表、趋势图和明细表中的显示。">
      <input type="checkbox" data-visible-partid="${partid}" ${isPartidVisible(partid) ? "checked" : ""}>
      <span><i></i>ID ${partid}</span>
    </label>
  `).join("");
  $("#selectedPartidCount").textContent = state.visiblePartids.size;
  $$("#partidVisibility [data-help]").forEach(bindHelpTarget);
}

function emptyPartidResources() {
  return Array.from({ length: 16 }, (_, partid) => ({
    partid,
    requesters: new Set(),
  }));
}

function aggregateCpuResources() {
  const result = emptyPartidResources().map((row) => ({
    ...row,
    outstanding: 0,
    peakOutstanding: 0,
    maxOutstanding: 0,
    effectiveMaxOutstanding: 0,
    cbusyLevel: 0,
    cbusyStallNs: 0,
    cbusyTransitions: 0,
    issued: 0,
    completed: 0,
    backpressureNs: 0,
    coreOutstanding: 0,
    corePeakOutstanding: 0,
    coreLimit: 0,
    corePartidOutstanding: 0,
    corePartidPeakOutstanding: 0,
    corePolicies: new Set(),
    cores: new Set(),
    destinations: new Map(),
  }));
  const configured = collectStimulusConfigs().filter((row) => row.enabled);
  configured.forEach((row) => {
    result[row.partid].requesters.add(row.requester);
    result[row.partid].cores.add(
      String(row.requester).replace(/\.t\d+$/, ""),
    );
  });
  const seenCorePartid = result.map(() => new Set());
  latestByKeys(state.partial.cpu || [], ["requester_id", "partid"]).forEach((row) => {
    const partid = Number(row.partid);
    if (!Number.isInteger(partid) || partid < 0 || partid > 15) return;
    const target = result[partid];
    target.requesters.add(String(row.requester_id));
    target.outstanding += Number(row.outstanding || 0);
    target.peakOutstanding += Number(row.peak_outstanding || 0);
    target.maxOutstanding += Number(row.max_outstanding || 0);
    target.effectiveMaxOutstanding += Number(
      row.effective_max_outstanding || row.max_outstanding || 0
    );
    target.cbusyLevel = Math.max(
      target.cbusyLevel,
      Number(row.cbusy_level || 0),
    );
    target.cbusyStallNs += Number(row.cbusy_stall_ns || 0);
    target.cbusyTransitions += Number(row.cbusy_transitions || 0);
    target.issued += Number(row.issued || 0);
    target.completed += Number(row.completed || 0);
    target.backpressureNs += Number(row.backpressure_ns || 0);
    const coreId = String(row.core_id || row.requester_id || "");
    if (!seenCorePartid[partid].has(coreId)) {
      seenCorePartid[partid].add(coreId);
      target.coreOutstanding += Number(row.core_ostd || 0);
      target.corePeakOutstanding += Number(row.core_ostd_peak || 0);
      target.coreLimit += Number(row.core_ostd_limit || 0);
      target.corePartidOutstanding += Number(
        row.core_partid_ostd || 0,
      );
      target.corePartidPeakOutstanding += Number(
        row.core_partid_ostd_peak || 0,
      );
      if (row.core_ostd_policy) {
        target.corePolicies.add(String(row.core_ostd_policy));
      }
    }
  });
  const seenCorePartidMc = result.map(() => new Set());
  latestByKeys(
    state.partial.cpu_mc || [],
    ["requester_id", "partid", "destination_mc"],
  ).forEach((row) => {
    const partid = Number(row.partid);
    if (!Number.isInteger(partid) || partid < 0 || partid > 15) return;
    const target = result[partid];
    const mcId = String(row.destination_mc || "-");
    if (!target.destinations.has(mcId)) {
      target.destinations.set(mcId, {
        outstanding: 0,
        peak: 0,
        limit: 0,
        cbusy: 0,
      });
    }
    const destination = target.destinations.get(mcId);
    const coreKey = `${row.core_id || row.requester_id}:${mcId}`;
    if (!seenCorePartidMc[partid].has(coreKey)) {
      seenCorePartidMc[partid].add(coreKey);
      destination.outstanding += Number(
        row.core_partid_mc_ostd ?? row.outstanding ?? 0,
      );
      destination.peak += Number(
        row.core_partid_mc_ostd_peak ?? row.peak_outstanding ?? 0,
      );
      destination.limit += Number(
        row.effective_max_outstanding || 0,
      );
    }
    destination.cbusy = Math.max(
      destination.cbusy,
      Number(row.cbusy_level || 0),
    );
  });
  const configuredMax = Number($('[data-param="max_outstanding"]')?.value || 0);
  const configuredCoreMax = Number(
    $('[data-param="core_max_outstanding"]')?.value || 0,
  );
  const configuredCorePolicy = String(
    $('[data-param="core_ostd_policy"]')?.value || "shared",
  );
  result.forEach((row) => {
    if (row.maxOutstanding === 0 && row.requesters.size) {
      row.maxOutstanding = row.requesters.size * configuredMax;
    }
    if (row.effectiveMaxOutstanding === 0 && row.requesters.size) {
      row.effectiveMaxOutstanding = row.maxOutstanding;
    }
    if (row.coreLimit === 0 && row.cores.size) {
      row.coreLimit = row.cores.size * configuredCoreMax;
    }
    if (!row.corePolicies.size && row.cores.size) {
      row.corePolicies.add(configuredCorePolicy);
    }
    row.outstandingUtilization = Math.min(
      1,
      row.outstanding / Math.max(1, row.effectiveMaxOutstanding),
    );
    row.completionRatio = row.completed / Math.max(1, row.issued);
    row.coreUtilization = Math.min(
      1,
      row.coreOutstanding / Math.max(1, row.coreLimit),
    );
  });
  return result;
}

function singleValue(values, fallback = "-") {
  const entries = [...values].filter((value) => value !== "" && value != null);
  if (!entries.length) return fallback;
  if (entries.length === 1) return entries[0];
  return entries.join(" / ");
}

function aggregateL3Resources() {
  const result = emptyPartidResources().map((row) => ({
    ...row,
    bandwidth: 0,
    occupancy: 0,
    rawOccupancy: 0,
    filteredOccupancy: 0,
    controlOccupancy: 0,
    actualOccupancy: 0,
    rawBandwidth: 0,
    filteredBandwidth: 0,
    monitorError: 0,
    capacity: 0,
    allowedCapacity: 0,
    requests: 0,
    hits: 0,
    misses: 0,
    allocationDenials: 0,
    queueDelayNs: 0,
    admissionBackpressureNs: 0,
    queueFullEvents: 0,
    queueOccupancy: 0,
    queuePeak: 0,
    queueDepth: 0,
    lookupParallelism: 0,
    mshrOccupancy: 0,
    mshrPeak: 0,
    mshrEntries: 0,
    mshrWaiting: 0,
    fillOccupancy: 0,
    fillPeak: 0,
    fillEntries: 0,
    mergedMisses: 0,
    allocationBypass: 0,
    redundantFetches: 0,
    cminByMsc: new Map(),
    cmaxByMsc: new Map(),
    cpbmByMsc: new Map(),
    configuredCminByMsc: new Map(),
    configuredCmaxByMsc: new Map(),
    configuredCpbmByMsc: new Map(),
    cminEnabled: false,
    cmaxEnabled: false,
    cpbmEnabled: false,
  }));
  latestBy(state.partial.msc, "msc_id")
    .filter((row) => row.msc_type === "cache")
    .forEach((row) => {
      result.forEach((target) => {
        target.queueOccupancy += Number(row.queue_occupancy || 0);
        target.queuePeak += Number(row.queue_peak || 0);
        target.queueDepth += Number(row.queue_depth || 0);
        target.lookupParallelism += Number(row.lookup_parallelism || 0);
        target.mshrOccupancy += Number(row.mshr_occupancy || 0);
        target.mshrPeak += Number(row.mshr_peak || 0);
        target.mshrEntries += Number(row.mshr_entries || 0);
        target.mshrWaiting += Number(row.mshr_waiting || 0);
        target.fillOccupancy += Number(
          row.fill_buffer_occupancy || 0,
        );
        target.fillPeak += Number(row.fill_buffer_peak || 0);
        target.fillEntries += Number(
          row.fill_buffer_entries || 0,
        );
      });
      Object.entries(row.per_partid || {}).forEach(([pidText, values]) => {
        const partid = Number(pidText);
        if (!Number.isInteger(partid) || partid < 0 || partid > 15) return;
        const target = result[partid];
        target.bandwidth += Number(
          values.filtered_bandwidth_gbps
          ?? values.estimated_bandwidth_gbps
          ?? 0,
        );
        target.rawBandwidth += Number(values.raw_bandwidth_gbps || 0);
        target.filteredBandwidth += Number(
          values.filtered_bandwidth_gbps || 0,
        );
        target.rawOccupancy += Number(values.raw_occupancy_bytes || 0);
        target.filteredOccupancy += Number(
          values.filtered_occupancy_bytes
          ?? values.estimated_occupancy_bytes
          ?? 0,
        );
        target.controlOccupancy += Number(
          values.control_occupancy_bytes
          ?? values.filtered_occupancy_bytes
          ?? values.estimated_occupancy_bytes
          ?? 0,
        );
        target.occupancy += Number(
          values.filtered_occupancy_bytes
          ?? values.estimated_occupancy_bytes
          ?? 0,
        );
        target.actualOccupancy += Number(
          values.actual_occupancy_bytes || 0,
        );
        target.monitorError += Number(values.monitor_error_bytes || 0);
        target.capacity += Number(values.cache_capacity_bytes || 0);
        target.allowedCapacity += Number(values.allowed_capacity_bytes || 0);
        target.requests += Number(values.requests || 0);
        target.hits += Number(values.hits || 0);
        target.misses += Number(values.misses || 0);
        target.allocationDenials += Number(values.allocation_denials || 0);
        target.queueDelayNs += Number(values.queue_delay_ns || 0);
        target.mergedMisses += Number(values.merged_misses || 0);
        target.allocationBypass += Number(
          values.allocation_bypass || 0,
        );
        target.redundantFetches += Number(
          values.redundant_memory_fetches || 0,
        );
        target.admissionBackpressureNs += Number(
          values.admission_backpressure_ns || 0,
        );
        target.queueFullEvents += Number(values.queue_full_events || 0);
        target.cminByMsc.set(String(row.msc_id), values.cmin_percent);
        target.cmaxByMsc.set(String(row.msc_id), values.cmax_percent);
        target.cpbmByMsc.set(String(row.msc_id), values.cpbm);
        target.configuredCminByMsc.set(
          String(row.msc_id),
          values.configured_cmin_percent,
        );
        target.configuredCmaxByMsc.set(
          String(row.msc_id),
          values.configured_cmax_percent,
        );
        target.configuredCpbmByMsc.set(
          String(row.msc_id),
          values.configured_cpbm,
        );
        target.cminEnabled ||= Boolean(values.cmin_enable);
        target.cmaxEnabled ||= Boolean(values.cmax_enable);
        target.cpbmEnabled ||= Boolean(values.cpbm_enable);
      });
    });
  visibleRows(state.partial.controls).forEach((update) => {
    const partid = Number(update.partid);
    if (!Number.isInteger(partid) || partid < 0 || partid > 15) return;
    const target = result[partid];
    const mscId = String(update.target_msc);
    if (update.field === "cache_min_percent") {
      target.cminByMsc.set(mscId, update.new_value);
    } else if (update.field === "cache_max_percent") {
      target.cmaxByMsc.set(mscId, update.new_value);
    } else if (update.field === "cache_portion_bitmap") {
      target.cpbmByMsc.set(mscId, update.new_value);
    }
  });
  result.forEach((row) => {
    const configured = state.partidConfigs[row.partid] || {};
    if (!row.configuredCminByMsc.size) {
      row.cminEnabled = Boolean(configured.cmin_enable);
      row.cmaxEnabled = Boolean(configured.cmax_enable);
      row.cpbmEnabled = Boolean(configured.cpbm_enable);
    }
    const cminValues = new Set(row.cminByMsc.values());
    const cmaxValues = new Set(row.cmaxByMsc.values());
    const cpbmValues = new Set(row.cpbmByMsc.values());
    if (!cminValues.size) cminValues.add(configured.cmin);
    if (!cmaxValues.size) cmaxValues.add(configured.cmax);
    if (!cpbmValues.size) cpbmValues.add(configured.cpbm);
    row.occupancyShare = row.occupancy / Math.max(1, row.capacity);
    row.occupancyUtilization = Math.min(1, row.occupancyShare);
    row.hitRate = row.hits / Math.max(1, row.hits + row.misses);
    row.cmin = singleValue(cminValues);
    row.cmax = singleValue(cmaxValues);
    row.cpbm = singleValue(cpbmValues);
    row.configuredCmin = singleValue(
      new Set(row.configuredCminByMsc.values()),
      configured.cmin,
    );
    row.configuredCmax = singleValue(
      new Set(row.configuredCmaxByMsc.values()),
      configured.cmax,
    );
    row.configuredCpbm = singleValue(
      new Set(row.configuredCpbmByMsc.values()),
      configured.cpbm,
    );
  });
  return result;
}

function aggregateMcResources() {
  const result = emptyPartidResources().map((row) => ({
    ...row,
    bandwidth: 0,
    capacity: 0,
    requests: 0,
    queueDelayNs: 0,
    throttleNs: 0,
    bminByMsc: new Map(),
    bmaxByMsc: new Map(),
    modeByMsc: new Map(),
    qosByMsc: new Map(),
    effectiveQosWeighted: 0,
    effectiveQosRequests: 0,
    configuredBminByMsc: new Map(),
    configuredBmaxByMsc: new Map(),
    configuredQosByMsc: new Map(),
    bminEnabled: false,
    bmaxEnabled: false,
    qosEnabled: false,
    softRequests: 0,
    softPenaltyEvents: 0,
    hardBlocks: 0,
    cbusyEnabled: false,
    cbusyLevel: 0,
    cbusyBandwidthRatio: 0,
    cbusyQueueRatio: 0,
    cbusyDuty: 0,
    cbusyTransitions: 0,
    cbusyCap: 0,
    rawBandwidth: 0,
    filteredBandwidth: 0,
    controlBandwidth: 0,
    underBmin: false,
    overBmax: false,
    hardBlock: false,
    bufferEntries: 0,
    candidates: 0,
    grants: 0,
    qosSaturation: 0,
    serviceDeficit: 0,
  }));
  latestBy(state.partial.msc, "msc_id")
    .filter((row) => row.msc_type === "memory_controller")
    .forEach((row) => {
      result.forEach((target) => {
        target.capacity += Number(row.total_bandwidth_gbps || 0);
      });
      Object.entries(row.per_partid || {}).forEach(([pidText, values]) => {
        const partid = Number(pidText);
        if (!Number.isInteger(partid) || partid < 0 || partid > 15) return;
        const target = result[partid];
        target.bandwidth += Number(values.achieved_bandwidth_gbps || 0);
        target.requests += Number(values.requests || 0);
        target.queueDelayNs += Number(values.queue_delay_ns || 0);
        target.throttleNs += Number(values.throttle_delay_ns || 0);
        target.bminByMsc.set(String(row.msc_id), values.bmin_gbps);
        target.bmaxByMsc.set(String(row.msc_id), values.bmax_gbps);
        target.modeByMsc.set(String(row.msc_id), values.limit_mode);
        target.qosByMsc.set(String(row.msc_id), values.base_qos);
        target.effectiveQosWeighted += Number(values.effective_qos_avg || 0)
          * Number(values.requests || 0);
        target.effectiveQosRequests += Number(values.requests || 0);
        target.configuredBminByMsc.set(
          String(row.msc_id),
          values.configured_bmin_gbps,
        );
        target.configuredBmaxByMsc.set(
          String(row.msc_id),
          values.configured_bmax_gbps,
        );
        target.configuredQosByMsc.set(
          String(row.msc_id),
          values.configured_mc_qos,
        );
        target.bminEnabled ||= Boolean(values.bmin_enable);
        target.bmaxEnabled ||= Boolean(values.bmax_enable);
        target.qosEnabled ||= Boolean(values.mc_qos_enable);
        target.softRequests += Number(values.softlimit_requests || 0);
        target.softPenaltyEvents += Number(
          values.softlimit_penalty_events || 0,
        );
        target.hardBlocks += Number(values.hardlimit_block_events || 0);
        target.rawBandwidth += Number(values.raw_bandwidth_gbps || 0);
        target.filteredBandwidth += Number(
          values.filtered_bandwidth_gbps || 0,
        );
        target.controlBandwidth += Number(
          values.control_bandwidth_gbps
          ?? values.filtered_bandwidth_gbps
          ?? 0,
        );
        target.underBmin ||= Boolean(values.under_bmin);
        target.overBmax ||= Boolean(values.over_bmax);
        target.hardBlock ||= Boolean(values.hard_block);
        target.bufferEntries += Number(values.buffer_entries || 0);
        target.candidates += Number(values.candidate_evaluations || 0);
        target.grants += Number(values.grants || 0);
        target.qosSaturation += Number(values.qos_saturation_events || 0);
        target.serviceDeficit = Math.max(
          target.serviceDeficit,
          Number(values.service_deficit || 0),
        );
        target.cbusyEnabled ||= Boolean(values.cbusy_enable);
        target.cbusyLevel = Math.max(
          target.cbusyLevel,
          Number(values.cbusy_level || 0),
        );
        target.cbusyBandwidthRatio = Math.max(
          target.cbusyBandwidthRatio,
          Number(
            values.cbusy_peak_bandwidth_ratio
            ?? values.cbusy_bandwidth_ratio
            ?? 0,
          ),
        );
        target.cbusyQueueRatio = Math.max(
          target.cbusyQueueRatio,
          Number(
            values.cbusy_peak_queue_ratio
            ?? values.cbusy_queue_ratio
            ?? 0,
          ),
        );
        target.cbusyDuty = Math.max(
          target.cbusyDuty,
          Number(values.cbusy_duty || 0),
        );
        target.cbusyTransitions += Number(values.cbusy_transitions || 0);
        if (Number(values.cbusy_level || 0) > 0) {
          target.cbusyCap = target.cbusyCap
            ? Math.min(target.cbusyCap, Number(values.cbusy_ostd_cap || 0))
            : Number(values.cbusy_ostd_cap || 0);
        }
      });
    });
  visibleRows(state.partial.controls).forEach((update) => {
    const partid = Number(update.partid);
    if (!Number.isInteger(partid) || partid < 0 || partid > 15) return;
    const target = result[partid];
    const mscId = String(update.target_msc);
    if (update.field === "bw_min_gbps") {
      target.bminByMsc.set(mscId, update.new_value);
    } else if (update.field === "bw_max_gbps") {
      target.bmaxByMsc.set(mscId, update.new_value);
    } else if (update.field === "bw_limit_mode") {
      target.modeByMsc.set(mscId, update.new_value);
    } else if (update.field === "mc_qos") {
      target.qosByMsc.set(mscId, update.new_value);
    }
  });
  result.forEach((row) => {
    const configured = state.partidConfigs[row.partid] || {};
    if (!row.configuredBminByMsc.size) {
      row.bminEnabled = Boolean(configured.bmin_enable);
      row.bmaxEnabled = Boolean(configured.bmax_enable);
      row.qosEnabled = Boolean(configured.mc_qos_enable);
    }
    if (!row.modeByMsc.size) {
      row.modeByMsc.set("configured", configured.limit_mode);
    }
    if (!row.qosByMsc.size) {
      row.qosByMsc.set("configured", configured.mc_qos);
    }
    if (!row.bminByMsc.size && configured.bmin_gbps != null) {
      row.bminByMsc.set("configured", configured.bmin_gbps);
    }
    if (!row.bmaxByMsc.size && configured.bmax_gbps != null) {
      row.bmaxByMsc.set("configured", configured.bmax_gbps);
    }
    const bminValues = [...row.bminByMsc.values()]
      .filter((value) => value != null);
    const bmaxValues = [...row.bmaxByMsc.values()]
      .filter((value) => value != null);
    row.bmin = bminValues.reduce((sum, value) => sum + Number(value), 0);
    row.bmax = bmaxValues.reduce((sum, value) => sum + Number(value), 0);
    row.hasBmin = bminValues.length > 0;
    row.hasBmax = bmaxValues.length > 0;
    row.bandwidthUtilization = Math.min(
      1,
      row.bandwidth / Math.max(1e-9, row.capacity),
    );
    row.avgQueueDelayNs = row.queueDelayNs / Math.max(1, row.requests);
    row.mode = singleValue(new Set(row.modeByMsc.values()));
    row.qos = singleValue(new Set(row.qosByMsc.values()));
    row.effectiveQos = (
      row.effectiveQosWeighted / Math.max(1, row.effectiveQosRequests)
    );
    row.configuredBmin = [...row.configuredBminByMsc.values()]
      .filter((value) => value != null)
      .reduce((sum, value) => sum + Number(value), 0);
    row.configuredBmax = [...row.configuredBmaxByMsc.values()]
      .filter((value) => value != null)
      .reduce((sum, value) => sum + Number(value), 0);
    row.configuredQos = singleValue(
      new Set(row.configuredQosByMsc.values()),
      configured.mc_qos,
    );
  });
  return result;
}

function aggregateRingResources() {
  const noc = latestBy(state.partial.msc || [], "msc_id")
    .find((row) => row.msc_type === "noc");
  if (!noc) return [];
  return Object.entries(noc.per_channel_direction || {})
    .map(([key, values]) => {
      const [channel, direction] = key.split(":");
      return {
        channel: channel.toUpperCase(),
        direction,
        offered: Number(values.offered_flits || 0),
        injected: Number(values.injected_flits || 0),
        ejected: Number(values.ejected_flits || 0),
        transfers: Number(values.completed_transfers || 0),
        failed: Number(values.failed_ejections || 0),
        laps: Number(values.full_laps || 0),
        hops: Number(values.hops || 0),
        backpressureEvents: Number(
          values.injection_backpressure_events || 0,
        ),
        backpressureNs: Number(
          values.injection_backpressure_ns || 0,
        ),
        slotOccupancy: Number(noc.slot_occupancy || 0),
        totalSlots: Number(noc.total_slots || 0),
        inFlight: Number(noc.in_flight_flits || 0),
        inFlightPeak: Number(noc.in_flight_peak || 0),
        sourcePending: Number(noc.source_pending_flits || 0),
      };
    })
    .sort((left, right) => (
      left.channel.localeCompare(right.channel)
      || left.direction.localeCompare(right.direction)
    ));
}

function controlValue(enabled, effective, configured, formatter = String) {
  const effectiveText = formatter(effective);
  const configuredText = formatter(configured);
  return enabled
    ? `<span class="control-value enabled">${effectiveText}</span>`
    : `<span class="control-value disabled">off</span><small>cfg ${configuredText}</small>`;
}

function controlFeedback(partid) {
  const updates = visibleRows(state.partial.controls)
    .filter(
      (row) =>
        Number(row.partid) === Number(partid)
        && row.policy !== "mc_cbusy",
    );
  const latest = updates[updates.length - 1] || null;
  const policy = $('input[name="policy"]:checked')?.value || "no_control";
  if (policy === "no_control") {
    return { state: "disabled", label: "无控制", latest, updates: updates.length };
  }
  if (policy === "static_mpam") {
    return { state: "static", label: "静态", latest, updates: updates.length };
  }
  return {
    state: latest ? "adjusted" : "monitoring",
    label: latest ? "已调整" : "监控中",
    latest,
    updates: updates.length,
  };
}

function controlStateCell(partid) {
  const feedback = controlFeedback(partid);
  const detail = feedback.latest
    ? `${formatTime(Number(feedback.latest.time_ns || 0))} · ${escapeHtml(feedback.latest.target_msc)} · ${escapeHtml(feedback.latest.field)}`
    : "暂无运行时更新";
  const reason = feedback.latest
    ? escapeHtml(feedback.latest.reason)
    : "";
  return `
    <div class="control-state-cell">
      <span class="control-state ${feedback.state}">${feedback.label}</span>
      <small>${detail}</small>
      ${reason ? `<small class="control-state-reason">${reason}</small>` : ""}
    </div>`;
}

function renderControlFeedbackSummary() {
  const policy = $('input[name="policy"]:checked')?.value || "no_control";
  const policyLabel = {
    no_control: "无控制",
    static_mpam: "静态 MPAM",
    closed_loop_qos: "闭环 QoS",
  }[policy] || policy;
  const updates = visibleRows(state.partial.controls)
    .filter((row) => isPartidVisible(row.partid));
  const latest = updates[updates.length - 1];
  $("#controlFeedbackSummary").innerHTML = `
    <span><b>反馈策略</b>${escapeHtml(policyLabel)}</span>
    <span><b>所选 PARTID 更新</b>${updates.length}</span>
    <span class="feedback-reason"><b>最近动作</b>${
      latest
        ? `${formatTime(Number(latest.time_ns || 0))} · PARTID ${escapeHtml(latest.partid)} · ${escapeHtml(latest.target_msc)}.${escapeHtml(latest.field)} · ${escapeHtml(latest.reason)}`
        : "暂无运行时控制更新"
    }</span>`;
}

function renderResourceMonitor() {
  renderPartidVisibility();
  renderControlFeedbackSummary();
  $("#resourceMonitorTime").textContent = formatTime(state.selectedTime || 0);
  const visible = (rows) => rows.filter((row) => isPartidVisible(row.partid));
  let headers = [];
  let rows = [];
  if (state.resourceView === "cpu") {
    headers = [
      "PARTID", "Control State", "Requester", "OSTD Current / Peak",
      "OSTD Util %", "Core Pool / ID OSTD", "Home MC ID OSTD",
      "CBusy", "Issued / Completed",
      "Backpressure ns", "CBusy Stall ns",
    ];
    rows = visible(aggregateCpuResources()).map((row) => `
      <tr>
        <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
        <td>${controlStateCell(row.partid)}</td>
        <td>${escapeHtml([...row.requesters].join(", ") || "-")}</td>
        <td><strong>${formatNumber(row.outstanding, 0)}</strong> / ${formatNumber(row.peakOutstanding, 0)} <small>eff ${formatNumber(row.effectiveMaxOutstanding, 0)} · cfg ${formatNumber(row.maxOutstanding, 0)}</small></td>
        <td>${utilizationCell(row.outstandingUtilization, partidColor(row.partid))}</td>
        <td><strong>${formatNumber(row.coreOutstanding, 0)}</strong> / ${formatNumber(row.corePeakOutstanding, 0)} <small>limit ${formatNumber(row.coreLimit, 0)} · ID ${formatNumber(row.corePartidOutstanding, 0)} / ${formatNumber(row.corePartidPeakOutstanding, 0)} · ${escapeHtml([...row.corePolicies].join(" / ") || "-")}</small></td>
        <td>${[...row.destinations.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([mcId, values]) => `<span class="destination-ostd"><b>${escapeHtml(mcId)}</b> ${formatNumber(values.outstanding, 0)} / ${formatNumber(values.peak, 0)} <small>cap ${formatNumber(values.limit, 0)} · L${formatNumber(values.cbusy, 0)}</small></span>`).join("") || "-"}</td>
        <td><span class="cbusy-level level-${row.cbusyLevel}">L${row.cbusyLevel}</span> <small>cap ${formatNumber(row.effectiveMaxOutstanding, 0)} · ${formatNumber(row.cbusyTransitions, 0)} trans</small></td>
        <td>${formatNumber(row.issued, 0)} / ${formatNumber(row.completed, 0)} <small>${(row.completionRatio * 100).toFixed(1)}%</small></td>
        <td>${formatNumber(row.backpressureNs, 2)}</td>
        <td>${formatNumber(row.cbusyStallNs, 2)}</td>
      </tr>`);
  } else if (state.resourceView === "ring") {
    headers = [
      "Channel", "Direction", "Offered / Injected",
      "Ejected / Transfers", "Slot Occupancy", "In Flight",
      "Source Pending", "Failed / Full Laps", "Hops",
      "Injection BP",
    ];
    rows = aggregateRingResources().map((row) => `
      <tr>
        <td><strong>${escapeHtml(row.channel)}</strong></td>
        <td>${escapeHtml(row.direction)}</td>
        <td>${formatNumber(row.offered, 0)} / ${formatNumber(row.injected, 0)}</td>
        <td>${formatNumber(row.ejected, 0)} / ${formatNumber(row.transfers, 0)}</td>
        <td>${formatNumber(row.slotOccupancy, 2)} / ${formatNumber(row.totalSlots, 0)}</td>
        <td>${formatNumber(row.inFlight, 0)} <small>peak ${formatNumber(row.inFlightPeak, 0)}</small></td>
        <td>${formatNumber(row.sourcePending, 0)}</td>
        <td>${formatNumber(row.failed, 0)} / ${formatNumber(row.laps, 0)}</td>
        <td>${formatNumber(row.hops, 0)}</td>
        <td>${formatNumber(row.backpressureEvents, 0)} <small>${formatNumber(row.backpressureNs, 2)} ns</small></td>
      </tr>`);
  } else if (state.resourceView === "l3") {
    headers = [
      "PARTID", "Control State", "Physical / Raw / Control",
      "Monitor Error", "L3 Util %", "Raw / Filtered BW",
      "Hit Rate", "L3 Queue",
      "MSHR", "Fill Buffer", "Queue Delay / Full",
      "Merge / Bypass", "Alloc Denials", "CMIN %", "CMAX %", "CPBM",
    ];
    rows = visible(aggregateL3Resources()).map((row) => `
      <tr>
        <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
        <td>${controlStateCell(row.partid)}</td>
        <td>${formatNumber(row.actualOccupancy, 0)} / ${formatNumber(row.rawOccupancy, 0)} / ${formatNumber(row.filteredOccupancy, 0)} B <small>capacity ${formatNumber(row.capacity, 0)} B · allowed ${formatNumber(row.allowedCapacity, 0)} B</small></td>
        <td>${formatNumber(row.monitorError, 0)} B</td>
        <td>${utilizationCell(row.occupancyUtilization, "#2d7a4c")}</td>
        <td>${formatNumber(row.rawBandwidth, 3)} / ${formatNumber(row.filteredBandwidth, 3)} Gbps</td>
        <td>${(row.hitRate * 100).toFixed(2)}%</td>
        <td>${formatNumber(row.queueOccupancy, 2)} / ${formatNumber(row.queueDepth, 0)} <small>peak ${formatNumber(row.queuePeak, 0)} · slots ${formatNumber(row.lookupParallelism, 0)}</small></td>
        <td>${formatNumber(row.mshrOccupancy, 0)} / ${formatNumber(row.mshrPeak, 0)} / ${formatNumber(row.mshrEntries, 0)} <small>${formatNumber(row.mshrWaiting, 0)} waiting</small></td>
        <td>${formatNumber(row.fillOccupancy, 0)} / ${formatNumber(row.fillPeak, 0)} / ${formatNumber(row.fillEntries, 0)}</td>
        <td>${formatNumber(row.queueDelayNs, 2)} ns <small>${formatNumber(row.queueFullEvents, 0)} full · ${formatNumber(row.admissionBackpressureNs, 2)} ns retry</small></td>
        <td>${formatNumber(row.mergedMisses, 0)} / ${formatNumber(row.allocationBypass, 0)} <small>${formatNumber(row.redundantFetches, 0)} redundant</small></td>
        <td>${formatNumber(row.allocationDenials, 0)}</td>
        <td>${controlValue(row.cminEnabled, row.cmin, row.configuredCmin, (value) => `${formatNumber(value, 1)}%`)}</td>
        <td>${controlValue(row.cmaxEnabled, row.cmax, row.configuredCmax, (value) => `${formatNumber(value, 1)}%`)}</td>
        <td>${controlValue(row.cpbmEnabled, row.cpbm, row.configuredCpbm, (value) => `<code>${escapeHtml(value)}</code>`)}</td>
      </tr>`);
  } else {
    headers = [
      "PARTID", "Control State", "MC BW", "Raw / Filtered BW",
      "Limit State", "Buffer / Candidate / Grant", "MC Util %",
      "Avg Queue ns", "Throttle ns", "CBusy Evidence", "BMIN Σ",
      "BMAX Σ", "Mode", "QoS Base / Eff", "Limit Events",
    ];
    rows = visible(aggregateMcResources()).map((row) => `
      <tr>
        <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
        <td>${controlStateCell(row.partid)}</td>
        <td>${formatNumber(row.bandwidth, 3)} Gbps</td>
        <td>${formatNumber(row.rawBandwidth, 3)} / ${formatNumber(row.filteredBandwidth, 3)} Gbps</td>
        <td><span class="control-value ${row.hardBlock ? "enabled" : "disabled"}">${row.hardBlock ? "HARD" : row.overBmax ? "OVER" : row.underBmin ? "UNDER" : "IN RANGE"}</span></td>
        <td>${formatNumber(row.bufferEntries, 0)} / ${formatNumber(row.candidates, 0)} / ${formatNumber(row.grants, 0)} <small>def ${formatNumber(row.serviceDeficit, 0)}</small></td>
        <td>${utilizationCell(row.bandwidthUtilization, "#176b9c")}</td>
        <td>${formatNumber(row.avgQueueDelayNs, 2)}</td>
        <td>${formatNumber(row.throttleNs, 2)}</td>
        <td>
          <span class="cbusy-level level-${row.cbusyLevel}">L${row.cbusyLevel}</span>
          <small>${row.cbusyEnabled ? `BW ${row.cbusyBandwidthRatio.toFixed(2)}x · Q ${(row.cbusyQueueRatio * 100).toFixed(1)}% · duty ${(row.cbusyDuty * 100).toFixed(0)}% · ${formatNumber(row.cbusyTransitions, 0)} trans` : "off"}</small>
        </td>
        <td>${controlValue(row.bminEnabled, row.hasBmin ? row.bmin : 0, row.configuredBmin, (value) => formatNumber(value, 1))}</td>
        <td>${controlValue(row.bmaxEnabled, row.hasBmax ? row.bmax : 0, row.configuredBmax, (value) => formatNumber(value, 1))}</td>
        <td>${row.bmaxEnabled ? escapeHtml(row.mode) : '<span class="control-value disabled">off</span>'}</td>
        <td>${controlValue(row.qosEnabled, `${row.qos} / ${formatNumber(row.effectiveQos, 2)}`, `${row.configuredQos} / -`, (value) => escapeHtml(value))}<small>${formatNumber(row.qosSaturation, 0)} saturated</small></td>
        <td>${formatNumber(row.softPenaltyEvents, 0)} soft penalty / ${formatNumber(row.hardBlocks, 0)} hard <small>${formatNumber(row.softRequests, 0)} selected over · ${formatNumber(row.requests, 0)} req</small></td>
      </tr>`);
  }
  $("#resourceMonitorHead").innerHTML = `<tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr>`;
  $(".resource-monitor-table").dataset.resourceView = state.resourceView;
  $("#resourceMonitorTable").innerHTML = rows.length
    ? rows.join("")
    : `<tr><td colspan="${headers.length}" class="empty-cell">未选择 PARTID；使用上方开关选择要显示的分区</td></tr>`;
  $$("#resourceMonitorHead th").forEach((header) => {
    const label = header.textContent.trim();
    if (label === "CMIN %") header.dataset.algorithm = "l3-cmin";
    if (label === "CMAX %") header.dataset.algorithm = "l3-cmax";
    if (label === "QoS Base / Eff") header.dataset.algorithm = "mc-qos";
    if (
      [
        "Channel",
        "Offered / Injected",
        "Ejected / Transfers",
        "Failed / Full Laps",
        "Injection BP",
      ].includes(label)
    ) {
      header.dataset.algorithm = "ring-transport";
    }
    if (!header.dataset.algorithm) setHelp(header, headerHelp[label]);
  });
}

function renderAll() {
  renderKpis();
  renderCharts();
  renderControlOverview();
  renderResourceMonitor();
  renderControlEffect();
  renderExperiment();
  renderControlVerification();
  renderCausalTimeline();
  renderResctrlMonData();
  renderPartidTable();
  renderMonitorGroupTable();
  renderMpamMonitorTable();
  renderMscTable();
  renderControlTable();
}

function syncPartidSelect(selector, selected) {
  const select = $(selector);
  if (!select) return;
  const current = String(selected);
  if (select.options.length !== 16) {
    select.innerHTML = Array.from(
      { length: 16 },
      (_, partid) => `<option value="${partid}">PARTID ${partid}</option>`,
    ).join("");
  }
  select.value = current;
}

function overviewLayerEnabled(layer) {
  return Boolean(state.overviewChartLayers[layer]);
}

function syncOverviewLayerControls() {
  $$("[data-overview-layer]").forEach((input) => {
    input.checked = overviewLayerEnabled(input.dataset.overviewLayer);
  });
}

function experimentCases() {
  if (state.experiment?.cases) return state.experiment.cases;
  const results = state.experimentPartial?.results || {};
  return ["reference", "bmax_only", "cbusy_only", "combined"]
    .map((caseId) => results[caseId])
    .filter(Boolean);
}

function deltaCell(value, baseline, lowerIsBetter, formatter) {
  const rendered = formatter(value);
  const base = Number(baseline);
  const current = Number(value);
  if (!Number.isFinite(base) || !Number.isFinite(current) || base === 0) {
    return rendered;
  }
  const change = (current - base) / Math.abs(base);
  if (Math.abs(change) < 0.001) {
    return `${rendered}<small class="delta neutral">0.0%</small>`;
  }
  const improvement = lowerIsBetter ? change < 0 : change > 0;
  return `${rendered}<small class="delta ${improvement ? "good" : "bad"}">${change > 0 ? "+" : ""}${(change * 100).toFixed(1)}%</small>`;
}

function renderExperiment() {
  syncPartidSelect("#experimentPartid", state.experimentPartid);
  const cases = experimentCases();
  const completed = state.experimentPartial?.completed_cases || [];
  $("#experimentProgress").textContent = state.experiment
    ? `已完成 4/4，seed ${state.experiment.seed}`
    : completed.length
      ? `已完成 ${completed.length}/4：${cases.map((row) => row.label).join("、")}`
      : "尚未运行对照实验";
  if (!cases.length) {
    $("#experimentTable").innerHTML = '<tr><td colspan="10" class="empty-cell">运行四组对照后显示结果</td></tr>';
    $("#experimentPartidTable").innerHTML = '<tr><td colspan="8" class="empty-cell">运行四组对照后显示所选 PARTID</td></tr>';
    return;
  }

  const baseline = cases.find((row) => row.id === "reference") || cases[0];
  $("#experimentTable").innerHTML = cases.map((row) => `
    <tr class="${row.id === "reference" ? "baseline-row" : ""}">
      <td><strong>${escapeHtml(row.label)}</strong>${row.report_url ? ` <a class="case-report-link" href="${escapeHtml(row.report_url)}" target="_blank">报告</a>` : ""}</td>
      <td>${deltaCell(row.total_throughput_gbps, baseline.total_throughput_gbps, false, (value) => formatNumber(value, 3))}</td>
      <td>${deltaCell(row.max_p99_latency_ns, baseline.max_p99_latency_ns, true, (value) => formatNumber(value, 2))}</td>
      <td>${deltaCell(row.completion_ratio, baseline.completion_ratio, false, (value) => `${(Number(value) * 100).toFixed(2)}%`)}</td>
      <td>${deltaCell(row.mc_queue_peak, baseline.mc_queue_peak, true, (value) => formatNumber(value, 2))}</td>
      <td>${deltaCell(row.mc_queue_area_entry_ns, baseline.mc_queue_area_entry_ns, true, (value) => formatNumber(value, 2))}</td>
      <td>${deltaCell(row.throttle_delay_ns, baseline.throttle_delay_ns, true, (value) => formatNumber(value, 2))}</td>
      <td>${deltaCell(row.cbusy_stall_ns, baseline.cbusy_stall_ns, true, (value) => formatNumber(value, 2))}</td>
      <td>${formatNumber(row.hard_blocks, 0)}</td>
      <td>${formatNumber(row.cbusy_transitions, 0)}</td>
    </tr>
  `).join("");

  const partid = String(state.experimentPartid);
  const baselinePartid = baseline.per_partid?.[partid] || {};
  const partidRows = cases
    .filter((row) => row.per_partid?.[partid])
    .map((row) => {
      const values = row.per_partid[partid];
      return `
        <tr class="${row.id === "reference" ? "baseline-row" : ""}">
          <td><strong>${escapeHtml(row.label)}</strong></td>
          <td>${deltaCell(values.throughput_gbps, baselinePartid.throughput_gbps, false, (value) => formatNumber(value, 3))}</td>
          <td>${deltaCell(values.p99_latency_ns, baselinePartid.p99_latency_ns, true, (value) => formatNumber(value, 2))}</td>
          <td>${deltaCell(values.queue_ratio_peak, baselinePartid.queue_ratio_peak, true, (value) => `${(Number(value) * 100).toFixed(1)}%`)}</td>
          <td>${formatNumber(values.effective_ostd_min, 0)}</td>
          <td>${formatNumber(values.cbusy_stall_ns, 2)}</td>
          <td>${formatNumber(values.throttle_delay_ns, 2)}</td>
          <td>${formatNumber(values.hard_blocks, 0)}</td>
        </tr>`;
    });
  $("#experimentPartidTable").innerHTML = partidRows.length
    ? partidRows.join("")
    : '<tr><td colspan="8" class="empty-cell">该 PARTID 在当前激励中没有请求</td></tr>';
}

function verificationCases() {
  if (state.verification?.cases) return state.verification.cases;
  const results = state.verificationPartial?.results || {};
  return [
    "cmin_off", "cmin_on", "cmax_full", "cmax_limited",
    "qos_equal", "qos_split",
    "bmin_off", "bmin_on", "bmax_solo_off", "bmax_solo_soft",
    "bmax_solo_hard", "bmax_contended_off", "bmax_contended_soft",
  ].map((caseId) => results[caseId]).filter(Boolean);
}

function renderControlVerification() {
  const cases = verificationCases();
  const completed = state.verificationPartial?.completed_cases || [];
  const algorithm = state.verification?.algorithm_parameters
    || ($$("[data-partid-row]").length
      ? collectParameters()
      : state.defaults);
  const algorithmText = `MC ${formatNumber(algorithm.mc_clock_mhz, 0)} MHz · ${formatNumber(algorithm.mc_monitor_period_cycles, 0)}拍 · filter ${formatNumber(algorithm.mc_history_weight, 2)}/${formatNumber(algorithm.mc_current_weight, 2)} · ${escapeHtml(algorithm.mc_aging_mode || "none")} +${formatNumber(algorithm.mc_qos_aging_max_steps, 0)}档 · BMIN +${formatNumber(algorithm.mc_bmin_qos_promote, 0)} · soft -${formatNumber(algorithm.mc_softlimit_qos_demote, 0)}`;
  $("#verificationProgress").textContent = state.verification
    ? `验证完成：${state.verification.passed}/${state.verification.total} 通过，seed ${state.verification.seed} · ${algorithmText}`
    : completed.length
      ? `已完成 ${completed.length}/13：${cases.map((row) => row.label).join("、")}`
      : `尚未运行算法验证 · ${algorithmText}`;
  const checks = state.verification?.checks || [];
  $("#verificationCheckTable").innerHTML = checks.length ? checks.map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.label)}</strong></td>
      <td><span class="verification-status ${row.passed ? "pass" : "fail"}">${row.passed ? "PASS" : "FAIL"}</span></td>
      <td>${escapeHtml(row.expected)}</td>
      <td>${escapeHtml(row.evidence)}</td>
    </tr>
  `).join("") : '<tr><td colspan="4" class="empty-cell">运行验证后显示机制判据</td></tr>';
  $("#verificationCaseTable").innerHTML = cases.length ? cases.map((row) => {
    const p0 = row.per_partid?.["0"] || {};
    return `
      <tr>
        <td><strong>${escapeHtml(row.label)}</strong></td>
        <td>${formatNumber(p0.throughput_gbps, 3)} Gbps</td>
        <td>${formatNumber(p0.p99_latency_ns, 2)} ns</td>
        <td>${formatNumber(p0.sampled_way_count, 0)}</td>
        <td>${formatNumber(p0.cmin_protected_candidates, 0)}</td>
        <td>${formatNumber(p0.bmin_priority_requests, 0)}</td>
        <td>${formatNumber(p0.softlimit_penalty_events, 0)}</td>
        <td>${formatNumber(p0.hardlimit_block_events, 0)}</td>
        <td><a class="case-report-link" href="${escapeHtml(row.report_url)}" target="_blank">打开</a></td>
      </tr>`;
  }).join("") : '<tr><td colspan="9" class="empty-cell">尚无验证 case</td></tr>';
}

function buildCausalRows(partid) {
  const pid = Number(partid);
  const times = new Set();
  visibleRows(state.partial.metrics)
    .filter((row) => Number(row.partid) === pid)
    .forEach((row) => times.add(Number(row.time_ns)));
  visibleRows(state.partial.cpu)
    .filter((row) => Number(row.partid) === pid)
    .forEach((row) => times.add(Number(row.time_ns)));
  visibleRows(state.partial.msc)
    .filter((row) => row.msc_type === "memory_controller")
    .forEach((row) => times.add(Number(row.time_ns)));

  const controls = visibleRows(state.partial.controls)
    .filter((row) => Number(row.partid) === pid);
  let previousTime = -1;
  return [...times].sort((a, b) => a - b).map((timeNs) => {
    const metrics = visibleRows(state.partial.metrics).find(
      (row) => Number(row.time_ns) === timeNs && Number(row.partid) === pid,
    ) || {};
    const cpuRows = visibleRows(state.partial.cpu).filter(
      (row) => Number(row.time_ns) === timeNs && Number(row.partid) === pid,
    );
    const mcRows = visibleRows(state.partial.msc).filter(
      (row) => Number(row.time_ns) === timeNs
        && row.msc_type === "memory_controller",
    );
    const mcValues = mcRows.map(
      (row) => row.per_partid?.[String(pid)] || {},
    );
    const events = controls.filter(
      (row) => Number(row.time_ns) > previousTime
        && Number(row.time_ns) <= timeNs,
    );
    previousTime = timeNs;
    return {
      timeNs,
      bandwidth: mcValues.reduce(
        (sum, row) => sum + Number(row.achieved_bandwidth_gbps || 0),
        0,
      ),
      queuePeak: Math.max(
        0,
        ...mcValues.map((row) => Number(
          row.cbusy_peak_queue_ratio ?? row.cbusy_queue_ratio ?? 0,
        )),
      ),
      cbusyLevel: Math.max(
        0,
        ...cpuRows.map((row) => Number(row.cbusy_level || 0)),
        ...mcValues.map((row) => Number(row.cbusy_level || 0)),
      ),
      outstanding: cpuRows.reduce(
        (sum, row) => sum + Number(row.outstanding || 0),
        0,
      ),
      effectiveCap: cpuRows.reduce(
        (sum, row) => sum + Number(
          row.effective_max_outstanding || row.max_outstanding || 0,
        ),
        0,
      ),
      cbusyStall: cpuRows.reduce(
        (sum, row) => sum + Number(row.cbusy_stall_ns || 0),
        0,
      ),
      p99: Number(metrics.p99_latency_ns || 0),
      throughput: Number(metrics.throughput_gbps || 0),
      events,
    };
  });
}

function renderCausalTimeline() {
  syncPartidSelect("#causalPartid", state.causalPartid);
  const rows = buildCausalRows(state.causalPartid);
  $("#causalTable").innerHTML = rows.length ? rows.map((row) => `
    <tr>
      <td>${formatTime(row.timeNs)}</td>
      <td>${formatNumber(row.bandwidth, 3)} Gbps</td>
      <td>${(row.queuePeak * 100).toFixed(1)}%</td>
      <td><span class="cbusy-level level-${row.cbusyLevel}">L${row.cbusyLevel}</span></td>
      <td>${formatNumber(row.outstanding, 0)} / ${formatNumber(row.effectiveCap, 0)}</td>
      <td>${formatNumber(row.cbusyStall, 2)} ns</td>
      <td>${formatNumber(row.p99, 2)} ns</td>
      <td>${formatNumber(row.throughput, 3)} Gbps</td>
      <td class="causal-events">${row.events.length ? row.events.map((event) =>
        `<span><b>${escapeHtml(event.target_msc)}</b> ${escapeHtml(event.field)} ${escapeHtml(event.old_value)}→${escapeHtml(event.new_value)} <small>${escapeHtml(event.reason)}</small></span>`
      ).join("") : '<span class="muted">无更新</span>'}</td>
    </tr>
  `).join("") : '<tr><td colspan="9" class="empty-cell">运行单次仿真后显示因果时间线</td></tr>';
}

function bitCountHex(value) {
  try {
    return [...BigInt(`0x${String(value).replace(/^0x/i, "") || "0"}`).toString(2)]
      .filter((bit) => bit === "1").length;
  } catch {
    return 0;
  }
}

function configurationDiagnostics() {
  if (!$$("[data-partid-row]").length || !$$("[data-stimulus-row]").length) {
    return [];
  }
  const parameters = collectParameters();
  const partids = parameters.partid_configs;
  const stimuli = parameters.stimulus_configs.filter((row) => row.enabled);
  const messages = [];
  const add = (severity, text) => messages.push({ severity, text });

  if (!stimuli.length) add("error", "没有启用的激励，仿真不会产生请求。");
  if (
    Math.abs(
      Number(parameters.mc_history_weight)
      + Number(parameters.mc_current_weight)
      - 1,
    ) > 1e-9
  ) {
    add("error", "MC History Weight 与 Current Weight 之和必须等于 1。");
  }
  if (
    Math.abs(
      Number(parameters.l3_history_weight)
      + Number(parameters.l3_current_weight)
      - 1,
    ) > 1e-9
  ) {
    add("error", "L3 History Weight 与 Current Weight 之和必须等于 1。");
  }
  const activePartids = new Set(stimuli.map((row) => row.partid));
  activePartids.forEach((partid) => {
    const row = partids[partid];
    if (row && !row.monitor_enable) {
      add("warning", `PARTID ${partid} 有激励但监控开关关闭。`);
    }
  });
  if (
    Number(parameters.l3_lookup_parallelism)
    >= Number(parameters.l3_queue_depth)
  ) {
    add(
      "warning",
      "L3 lookup 并发槽不少于等待队列深度，常规流量下可能很难形成可观察的 L3 排队。",
    );
  }
  if (
    partids.some((row) => row.bmin_enable && activePartids.has(row.partid))
    && Number(parameters.mc_bmin_qos_promote) === 0
  ) {
    add("warning", "存在活动 BMIN，但 BMIN QoS 升档为 0；当前算法不会产生调度偏好。");
  }
  if (
    partids.some(
      (row) => row.bmax_enable
        && row.limit_mode === "softlimit"
        && activePartids.has(row.partid),
    )
    && Number(parameters.mc_softlimit_qos_demote) === 0
  ) {
    add("warning", "存在活动 softlimit BMAX，但 QoS 降档为 0；超限流量仍保持原 QoS。");
  }

  partids.forEach((row) => {
    if (row.cmin_enable && row.cmax_enable && row.cmin > row.cmax) {
      add("error", `PARTID ${row.partid} 的 CMIN 大于 CMAX。`);
    }
    if (row.cpbm_enable && bitCountHex(row.cpbm) === 0) {
      add("error", `PARTID ${row.partid} 的 CPBM 没有允许任何 way。`);
    }
    const reachable = bitCountHex(row.cpbm)
      * 100 / Math.max(1, Number(parameters.l3_ways));
    if (row.cmin_enable && row.cpbm_enable && row.cmin > reachable + 1e-9) {
      add("error", `PARTID ${row.partid} 的 CMIN ${row.cmin}% 超过 CPBM 可达比例 ${formatNumber(reachable, 1)}%。`);
    }
    if (row.bmax_enable && row.bmax_gbps <= 0) {
      add("error", `PARTID ${row.partid} 启用 BMAX，但配置值不大于 0。`);
    }
    if (
      row.bmin_enable && row.bmax_enable
      && row.bmin_gbps > row.bmax_gbps
    ) {
      add("error", `PARTID ${row.partid} 的 BMIN 大于 BMAX。`);
    }
    if (
      row.cbusy_l1_ostd < row.cbusy_l2_ostd
      || row.cbusy_l2_ostd < row.cbusy_l3_ostd
    ) {
      add("error", `PARTID ${row.partid} 的 CBusy OSTD 应满足 L1 ≥ L2 ≥ L3。`);
    }
    if (
      row.bmax_enable && row.limit_mode === "hardlimit"
      && row.cbusy_enable && activePartids.has(row.partid)
    ) {
      add("warning", `PARTID ${row.partid} 同时启用 hard BMAX 和 CBusy，可能出现 MC 阻塞与源端限流叠加；建议运行四组对照。`);
    }
  });

  const controllerBandwidth = Number(parameters.channels_per_mc)
    * Number(parameters.channel_bandwidth_gbps);
  const bminTotal = partids.reduce(
    (sum, row) => sum + (row.bmin_enable ? row.bmin_gbps : 0),
    0,
  );
  if (bminTotal > controllerBandwidth) {
    add("warning", `每个 MC 的启用 BMIN 合计 ${formatNumber(bminTotal, 1)} Gbps，超过单 MC 建模带宽 ${formatNumber(controllerBandwidth, 1)} Gbps。`);
  }
  const cminTotal = partids.reduce(
    (sum, row) => sum + (row.cmin_enable ? Number(row.cmin) : 0),
    0,
  );
  if (cminTotal > 100 + 1e-9) {
    add("error", `每个 L3 的启用 CMIN 合计 ${formatNumber(cminTotal, 1)}%，超过 100%。`);
  }
  if (
    Number(parameters.cbusy_sample_ns)
      * Number(parameters.cbusy_release_hold_samples)
    > Number(parameters.control_interval_ns)
  ) {
    add("warning", "CBusy 完整释放保持时间长于软件控制周期，快慢环可能在不同时间尺度上同时作用。");
  }
  const bandwidthThresholds = [
    parameters.cbusy_l1_bw_ratio,
    parameters.cbusy_l2_bw_ratio,
    parameters.cbusy_l3_bw_ratio,
  ].map(Number);
  const queueThresholds = [
    parameters.cbusy_l1_queue_ratio,
    parameters.cbusy_l2_queue_ratio,
    parameters.cbusy_l3_queue_ratio,
  ].map(Number);
  if (
    bandwidthThresholds[0] > bandwidthThresholds[1]
    || bandwidthThresholds[1] > bandwidthThresholds[2]
  ) add("error", "CBusy 带宽阈值应满足 L1 ≤ L2 ≤ L3。");
  if (
    queueThresholds[0] > queueThresholds[1]
    || queueThresholds[1] > queueThresholds[2]
  ) add("error", "CBusy 队列阈值应满足 L1 ≤ L2 ≤ L3。");
  resctrlDiagnostics()
    .filter((row) => row.severity !== "ok")
    .forEach((row) => add(row.severity, row.text));
  if (!messages.length) {
    add("ok", `配置检查通过：${stimuli.length} 个激励，${activePartids.size} 个活动 PARTID。`);
  }
  return messages;
}

function renderResctrlInfoSummary() {
  const target = $("#resctrlInfoSummary span");
  if (!target) return;
  const l3 = Number($('[data-param="l3_instances"]')?.value || 1);
  const mc = Number($('[data-param="memory_controllers"]')?.value || 1);
  const ways = Number($('[data-param="l3_ways"]')?.value || 16);
  const channels = Number($('[data-param="channels_per_mc"]')?.value || 1);
  const channelGbps = Number($('[data-param="channel_bandwidth_gbps"]')?.value || 0);
  target.textContent = `L3 domains 0..${Math.max(0, l3 - 1)} · MB domains 0..${Math.max(0, mc - 1)} · CBM ${ways}bit · MB ${formatNumber(channels * channelGbps, 1)} Gbps/domain`;
}

function resctrlDiagnostics() {
  const enabled = Boolean($('[data-param="resctrl_enabled"]')?.checked);
  if (!enabled) return [{ severity: "ok", text: "last_cmd_status: disabled，当前使用原始线程PARTID/PMG模式。" }];
  const groups = collectResctrlGroups().filter((row) => row.enabled || row.name === "root");
  const messages = [];
  const names = new Set();
  const partids = new Set();
  const taskOwners = new Map();
  const nonRootCpuOwners = new Map();
  const add = (severity, text) => messages.push({ severity, text });
  if (!groups.some((row) => row.name === "root")) {
    add("warning", "缺少root group；服务端会自动补root。");
  }
  groups.forEach((group) => {
    if (!group.name || group.name.includes("/")) {
      add("error", "CTRL_MON group名称不能为空且不能包含/。");
    }
    if (names.has(group.name)) add("error", `CTRL_MON group重复：${group.name}`);
    names.add(group.name);
    if (!Number.isInteger(group.partid) || group.partid < 0 || group.partid > 15) {
      add("error", `${group.name} PARTID必须为0..15。`);
    }
    if (partids.has(group.partid)) add("error", `PARTID ${group.partid}被多个CTRL_MON group使用。`);
    partids.add(group.partid);
    String(group.schemata || "").split("\n").filter((line) => line.trim()).forEach((line) => {
      if (!/^(L3|MB):/i.test(line.trim())) {
        add("error", `${group.name} schemata仅支持L3:或MB:行。`);
      }
    });
    parseSlotSet(group.tasks).forEach((slot) => {
      if (taskOwners.has(slot)) {
        add("error", `thread_${String(slot).padStart(2, "0")}被多个tasks列表显式分配。`);
      }
      taskOwners.set(slot, group.name);
    });
    if (group.name !== "root") {
      parseSlotSet(group.cpus, false).forEach((slot) => {
        if (nonRootCpuOwners.has(slot)) {
          add("error", `CPU ${slot}被多个非root cpus_list分配。`);
        }
        nonRootCpuOwners.set(slot, group.name);
      });
    }
  });
  if (!messages.length) {
    const activeGroups = groups.map((row) => `${row.name}->PARTID ${row.partid}`).join(", ");
    add("ok", `last_cmd_status: ok，${groups.length}个CTRL_MON group：${activeGroups}`);
  }
  return messages;
}

function renderResctrlStatus() {
  renderResctrlInfoSummary();
  const target = $("#resctrlLastStatus");
  if (!target) return;
  const diagnostics = resctrlDiagnostics();
  const first = diagnostics.find((row) => row.severity === "error")
    || diagnostics.find((row) => row.severity === "warning")
    || diagnostics[0];
  target.classList.toggle("error", first?.severity === "error");
  target.classList.toggle("warning", first?.severity === "warning");
  target.textContent = first?.text || "last_cmd_status: ok";
}

function renderResctrlMonData() {
  const target = $("#resctrlMonDataTable");
  if (!target) return;
  const enabled = Boolean($('[data-param="resctrl_enabled"]')?.checked);
  if (!enabled) {
    target.innerHTML = '<tr><td colspan="6" class="empty-cell">resctrl-like模式未启用</td></tr>';
    return;
  }
  const assignments = resctrlAssignments();
  const rowsByKey = new Map();
  assignments.forEach((assignment) => {
    const key = `${assignment.group.name}:${assignment.partid}:${assignment.pmg}`;
    if (!rowsByKey.has(key)) {
      rowsByKey.set(key, {
        group: assignment.group.name,
        monGroup: assignment.monGroup,
        partid: assignment.partid,
        pmg: assignment.pmg,
        requesters: [],
        llc: 0,
        mbmTotal: 0,
        mbmLocal: 0,
      });
    }
    rowsByKey.get(key).requesters.push(
      `cpu${Math.floor(assignment.slot / 2)}.t${assignment.slot % 2}`,
    );
  });
  latestBy(state.partial.msc || [], "msc_id")
    .filter((msc) => msc.msc_type === "cache")
    .forEach((msc) => {
      Object.entries(msc.monitor_groups || {}).forEach(([key, values]) => {
        const lookup = [...rowsByKey.values()].find((row) =>
          `${row.partid}:${row.pmg}` === key
        );
        if (!lookup) return;
        lookup.llc += Number(values.estimated_occupancy_bytes || 0);
      });
    });
  visibleRows(state.partial.msc || [])
    .filter((msc) => msc.msc_type === "memory_controller")
    .forEach((msc) => {
    Object.entries(msc.monitor_groups || {}).forEach(([key, values]) => {
      const lookup = [...rowsByKey.values()].find((row) =>
        `${row.partid}:${row.pmg}` === key
      );
      if (!lookup) return;
      lookup.mbmTotal += Number(values.bytes || 0);
      lookup.mbmLocal += Number(values.bytes || 0);
    });
  });
  const rows = [...rowsByKey.values()]
    .sort((left, right) => left.partid - right.partid || left.pmg - right.pmg);
  target.innerHTML = rows.length ? rows.map((row) => `
    <tr>
      <td><strong>${escapeHtml(row.group)}</strong>${row.monGroup ? `<small> / ${escapeHtml(row.monGroup)}</small>` : ""}</td>
      <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span> / G${row.pmg}</td>
      <td>${escapeHtml(row.requesters.join(", "))}</td>
      <td>${formatBytes(row.llc)}</td>
      <td>${formatBytes(row.mbmTotal)}</td>
      <td>${formatBytes(row.mbmLocal)}</td>
    </tr>
  `).join("") : '<tr><td colspan="6" class="empty-cell">暂无resctrl软件组映射</td></tr>';
}

function renderConfigDiagnostics() {
  renderSocCapabilitySummaries();
  renderResctrlStatus();
  renderResctrlMonData();
  const diagnostics = configurationDiagnostics();
  $("#configDiagnostics").innerHTML = diagnostics.map((row) => `
    <div class="diagnostic ${row.severity}">
      <b>${row.severity === "error" ? "错误" : row.severity === "warning" ? "注意" : "通过"}</b>
      <span>${escapeHtml(row.text)}</span>
    </div>
  `).join("");
}

function configuredMonitorGroups() {
  const groups = new Map();
  collectStimulusConfigs()
    .filter((row) => row.enabled)
    .forEach((row) => {
      const key = `${row.partid}:${row.pmg}`;
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          partid: row.partid,
          pmg: row.pmg,
          requesters: [],
          l3Bandwidth: 0,
          l3Occupancy: 0,
          l3Capacity: 0,
          mcBandwidth: 0,
          mcCapacity: 0,
          mcRequests: 0,
          throttleNs: 0,
        });
      }
      groups.get(key).requesters.push(row.requester);
    });
  return groups;
}

function aggregateMonitorGroups() {
  const groups = configuredMonitorGroups();
  latestBy(state.partial.msc, "msc_id").forEach((row) => {
    Object.entries(row.monitor_groups || {}).forEach(([key, values]) => {
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          partid: Number(values.partid),
          pmg: Number(values.pmg),
          requesters: [],
          l3Bandwidth: 0,
          l3Occupancy: 0,
          l3Capacity: 0,
          mcBandwidth: 0,
          mcCapacity: 0,
          mcRequests: 0,
          throttleNs: 0,
        });
      }
      const group = groups.get(key);
      if (row.msc_type === "cache") {
        group.l3Bandwidth += Number(values.estimated_bandwidth_gbps || 0);
        group.l3Occupancy += Number(values.estimated_occupancy_bytes || 0);
        group.l3Capacity += Number(values.allowed_capacity_bytes || 0);
      } else if (row.msc_type === "memory_controller") {
        group.mcBandwidth += Number(values.achieved_bandwidth_gbps || 0);
        group.mcCapacity += Number(values.controller_bandwidth_gbps || 0);
        group.mcRequests += Number(values.requests || 0);
        group.throttleNs += Number(values.throttle_delay_ns || 0);
      }
    });
  });
  return [...groups.values()]
    .map((group) => ({
      ...group,
      l3OccupancyRate: Math.min(
        1,
        group.l3Occupancy / Math.max(1, group.l3Capacity),
      ),
      mcUtilization: Math.min(
        1,
        group.mcBandwidth / Math.max(1e-9, group.mcCapacity),
      ),
    }))
    .sort((a, b) => a.partid - b.partid || a.pmg - b.pmg);
}

function utilizationCell(value, color) {
  const percent = Math.max(0, Math.min(100, Number(value || 0) * 100));
  return `
    <div class="utilization-cell">
      <span>${percent.toFixed(2)}%</span>
      <i><b style="width:${percent}%;background:${color}"></b></i>
    </div>`;
}

function renderMonitorGroupTable() {
  const rows = aggregateMonitorGroups().filter((row) => isPartidVisible(row.partid));
  $("#monitorGroupTime").textContent = formatTime(state.selectedTime || 0);
  $("#monitorGroupTable").innerHTML = rows.length ? rows.map((row) => `
    <tr>
      <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span> / G${row.pmg}</td>
      <td>${escapeHtml(row.requesters.join(", ") || "-")}</td>
      <td>${formatNumber(row.l3Bandwidth, 3)} Gbps</td>
      <td>${formatNumber(row.l3Occupancy, 0)} B</td>
      <td>${utilizationCell(row.l3OccupancyRate, "#2d7a4c")}</td>
      <td>${formatNumber(row.mcBandwidth, 3)} Gbps</td>
      <td>${utilizationCell(row.mcUtilization, "#176b9c")}</td>
      <td>${formatNumber(row.mcRequests, 0)}</td>
      <td>${formatNumber(row.throttleNs, 2)}</td>
    </tr>
  `).join("") : '<tr><td colspan="9" class="empty-cell">尚无监控组结果</td></tr>';
}

function renderKpis() {
  const summary = state.result?.summary;
  if (summary && state.selectedTime >= summary.simulation_time_ns) {
    $("#kpiThroughput").textContent = formatNumber(summary.total_throughput_gbps, 1);
    $("#kpiP99").textContent = formatNumber(summary.max_p99_latency_ns, 1);
    $("#kpiRequests").textContent = formatNumber(summary.completed_requests, 0);
    $("#kpiCompletion").textContent = (summary.completion_ratio * 100).toFixed(2);
    return;
  }
  const latest = latestBy(state.partial.metrics, "partid");
  const throughput = latest.reduce((sum, row) => sum + Number(row.throughput_gbps || 0), 0);
  const p99 = Math.max(0, ...latest.map((row) => Number(row.p99_latency_ns || 0)));
  const requests = latest.reduce((sum, row) => sum + Number(row.requests || 0), 0);
  $("#kpiThroughput").textContent = latest.length ? formatNumber(throughput, 1) : "--";
  $("#kpiP99").textContent = latest.length ? formatNumber(p99, 1) : "--";
  $("#kpiRequests").textContent = latest.length ? formatNumber(requests, 0) : "--";
  $("#kpiCompletion").textContent = state.result ? (state.result.summary.completion_ratio * 100).toFixed(2) : "--";
}

function prepareCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(rect.width * ratio));
  canvas.height = Math.max(1, Math.round(rect.height * ratio));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { ctx, width: rect.width, height: rect.height };
}

function axisLabel(label, unit) {
  const labelText = String(label || "").trim();
  const unitText = String(unit || "").trim();
  if (labelText && unitText) return `${labelText} (${unitText})`;
  return labelText || unitText;
}

function drawLineChart(canvas, series, options = {}) {
  const { ctx, width, height } = prepareCanvas(canvas);
  const pad = { left: 54, right: 15, top: 24, bottom: 34 };
  ctx.clearRect(0, 0, width, height);
  const xAxisText = axisLabel(options.xLabel || "时间", options.xUnit || "ns");
  const yAxisText = axisLabel(options.yLabel || "Y", options.yUnit);
  const normalizedSeries = series.map((entry) => ({
    ...entry,
    points: (entry.points || []).filter(
      (point) => Number.isFinite(point.x) && Number.isFinite(point.y),
    ),
  }));
  const points = normalizedSeries.flatMap((entry) => entry.points);
  const bandValues = (options.bands || []).flatMap((band) => [
    Number(band.from),
    Number(band.to),
  ]).filter(Number.isFinite);
  if (!points.length) {
    ctx.fillStyle = "#7b8790";
    ctx.font = "12px sans-serif";
    ctx.fillText("等待仿真数据", 16, 34);
    ctx.fillStyle = colors.axis;
    ctx.font = "10px sans-serif";
    if (yAxisText) ctx.fillText(yAxisText, 16, 14);
    if (xAxisText) ctx.fillText(xAxisText, 16, height - 10);
    return;
  }
  const maxX = Math.max(1, ...points.map((point) => point.x));
  const maxY = Number(options.yMax)
    || Math.max(1, ...points.map((point) => point.y), ...bandValues) * 1.08;
  const x = (value) => pad.left + (value / maxX) * (width - pad.left - pad.right);
  const y = (value) => height - pad.bottom - (value / maxY) * (height - pad.top - pad.bottom);

  (options.bands || []).forEach((band) => {
    const from = Number(band.from);
    const to = Number(band.to);
    if (!Number.isFinite(from) || !Number.isFinite(to)) return;
    const low = Math.max(0, Math.min(from, to));
    const high = Math.min(maxY, Math.max(from, to));
    if (high < low) return;
    ctx.save();
    ctx.fillStyle = band.color || "rgba(45, 122, 76, 0.12)";
    const top = y(high);
    const bottom = y(low);
    ctx.fillRect(pad.left, top, width - pad.left - pad.right, Math.max(1, bottom - top));
    ctx.restore();
  });

  ctx.strokeStyle = colors.grid;
  ctx.lineWidth = 1;
  ctx.fillStyle = colors.axis;
  ctx.font = "10px sans-serif";
  for (let index = 0; index <= 4; index += 1) {
    const py = pad.top + (index / 4) * (height - pad.top - pad.bottom);
    const value = maxY * (1 - index / 4);
    ctx.beginPath();
    ctx.moveTo(pad.left, py);
    ctx.lineTo(width - pad.right, py);
    ctx.stroke();
    ctx.fillText(formatNumber(value, value < 10 ? 2 : 0), 3, py + 3);
  }
  ctx.strokeStyle = colors.axis;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, height - pad.bottom);
  ctx.lineTo(width - pad.right, height - pad.bottom);
  ctx.stroke();
  ctx.fillStyle = colors.axis;
  ctx.font = "10px sans-serif";
  ctx.textAlign = "left";
  if (yAxisText) ctx.fillText(yAxisText, pad.left, 12);
  if (xAxisText) ctx.fillText(xAxisText, pad.left, height - 8);
  ctx.textAlign = "right";
  ctx.fillText(formatTime(maxX), width - pad.right, height - 8);
  ctx.textAlign = "left";

  (options.eventXs || []).forEach((eventX) => {
    if (!Number.isFinite(eventX)) return;
    ctx.save();
    ctx.strokeStyle = options.eventColor || colors.amber;
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 4]);
    ctx.beginPath();
    ctx.moveTo(x(eventX), pad.top);
    ctx.lineTo(x(eventX), height - pad.bottom);
    ctx.stroke();
    ctx.restore();
  });

  normalizedSeries.forEach((entry) => {
    if (!entry.points.length) return;
    ctx.save();
    ctx.strokeStyle = entry.color;
    ctx.lineWidth = entry.width || 2;
    ctx.setLineDash(entry.dash || []);
    ctx.beginPath();
    entry.points.forEach((point, index) => {
      if (index === 0) ctx.moveTo(x(point.x), y(point.y));
      else if (entry.step) {
        const previous = entry.points[index - 1];
        ctx.lineTo(x(point.x), y(previous.y));
        ctx.lineTo(x(point.x), y(point.y));
      } else {
        ctx.lineTo(x(point.x), y(point.y));
      }
    });
    ctx.stroke();
    ctx.fillStyle = entry.color;
    if (entry.marker === "points") {
      const stride = Math.max(1, Math.ceil(entry.points.length / 28));
      entry.points.forEach((point, index) => {
        if (index % stride !== 0 && index !== entry.points.length - 1) return;
        ctx.beginPath();
        ctx.arc(x(point.x), y(point.y), entry.markerRadius || 2.4, 0, Math.PI * 2);
        ctx.fill();
      });
    } else if (entry.marker !== "none") {
      const last = entry.points[entry.points.length - 1];
      ctx.beginPath();
      ctx.arc(x(last.x), y(last.y), entry.markerRadius || 3.2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  });
}

function drawBarChart(canvas, bars, options = {}) {
  const { ctx, width, height } = prepareCanvas(canvas);
  ctx.clearRect(0, 0, width, height);
  const xAxisText = axisLabel(options.xLabel || "类别", options.xUnit);
  const yAxisText = axisLabel(options.yLabel || "Y", options.yUnit);
  if (!bars.length) {
    ctx.fillStyle = "#7b8790";
    ctx.font = "12px sans-serif";
    ctx.fillText("等待仿真数据", 16, 34);
    ctx.fillStyle = colors.axis;
    ctx.font = "10px sans-serif";
    if (yAxisText) ctx.fillText(yAxisText, 16, 14);
    if (xAxisText) ctx.fillText(xAxisText, 16, height - 10);
    return;
  }
  const pad = { left: 50, right: 12, top: 24, bottom: 52 };
  const maxY = Math.max(1, ...bars.map((bar) => bar.value)) * 1.1;
  const gap = 10;
  const barWidth = Math.max(16, (width - pad.left - pad.right - gap * (bars.length - 1)) / bars.length);
  ctx.strokeStyle = colors.grid;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, height - pad.bottom);
  ctx.lineTo(width - pad.right, height - pad.bottom);
  ctx.stroke();
  bars.forEach((bar, index) => {
    const x = pad.left + index * (barWidth + gap);
    const barHeight = (bar.value / maxY) * (height - pad.top - pad.bottom);
    const y = height - pad.bottom - barHeight;
    ctx.fillStyle = bar.color;
    ctx.fillRect(x, y, barWidth, barHeight);
    ctx.fillStyle = colors.axis;
    ctx.font = "9px sans-serif";
    ctx.save();
    ctx.translate(x + barWidth / 2, height - pad.bottom + 7);
    ctx.rotate(-0.35);
    ctx.textAlign = "right";
    ctx.fillText(bar.label, 0, 0);
    ctx.restore();
    ctx.textAlign = "center";
    ctx.fillText(formatNumber(bar.value, 1), x + barWidth / 2, Math.max(10, y - 4));
  });
  ctx.fillStyle = colors.axis;
  ctx.font = "10px sans-serif";
  ctx.textAlign = "left";
  if (yAxisText) ctx.fillText(yAxisText, pad.left, 12);
  if (xAxisText) ctx.fillText(xAxisText, pad.left, height - 8);
}

function metricSeries(key) {
  const rows = visibleRows(state.partial.metrics)
    .filter((row) => isPartidVisible(row.partid));
  const partids = [...new Set(rows.map((row) => String(row.partid)))].sort(
    (a, b) => Number(a) - Number(b),
  );
  return partids.map((partid) => ({
    partid,
    color: partidColor(partid),
    points: rows
      .filter((row) => String(row.partid) === partid)
      .map((row) => ({ x: Number(row.time_ns), y: Number(row[key] || 0) })),
  }));
}

function legendItem({ color, label, kind = "solid" }) {
  if (kind === "dot") {
    return `<span><i style="background:${escapeHtml(color)}"></i>${escapeHtml(label)}</span>`;
  }
  const classes = {
    configured: "legend-line dotted",
    effective: "legend-line dashed",
    actual: "legend-line thin",
    raw: "legend-line points",
    filtered: "legend-line thick",
    event: "legend-line dashed",
    band: "legend-band",
    solid: "legend-line",
  };
  return `<span><i class="${classes[kind] || classes.solid}" style="--legend-color:${escapeHtml(color)}"></i>${escapeHtml(label)}</span>`;
}

function renderLegend(selector, entries) {
  const target = $(selector);
  if (!target) return;
  target.innerHTML = entries.map(legendItem).join("");
}

function renderCharts() {
  const latencySeries = metricSeries("p99_latency_ns");
  renderLegend(
    "#latencyLegend",
    latencySeries.map((entry) => ({
      color: entry.color,
      label: `ID ${entry.partid}`,
      kind: "dot",
    })),
  );
  drawLineChart($("#latencyChart"), latencySeries, {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "P99延迟",
    yUnit: "ns",
  });
  const bandwidthSeries = metricSeries("throughput_gbps");
  renderLegend(
    "#bandwidthLegend",
    bandwidthSeries.map((entry) => ({
      color: entry.color,
      label: `ID ${entry.partid}`,
      kind: "dot",
    })),
  );
  drawLineChart($("#bandwidthChart"), bandwidthSeries, {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "有效带宽",
    yUnit: "Gbps",
  });

  const queueRows = visibleRows(state.partial.msc);
  const groups = new Map();
  queueRows.forEach((row) => {
    const id = String(row.msc_id);
    if (!groups.has(id)) {
      groups.set(id, {
        label: id,
        color: id === "noc" ? colors.green : colors.amber,
        points: [],
      });
    }
    groups.get(id).points.push({ x: Number(row.time_ns), y: Number(row.queue_occupancy || 0) });
  });
  const queueSeries = [...groups.values()];
  renderLegend(
    "#queueLegend",
    queueSeries.map((entry) => ({
      color: entry.color,
      label: entry.label,
      kind: "solid",
    })),
  );
  drawLineChart($("#queueChart"), queueSeries, {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "队列占用",
    yUnit: "entries",
  });

  const latest = latestBy(state.partial.metrics, "partid");
  const targetStimulus = collectStimulusConfigs().find(
    (row) => row.enabled && row.target_p99_ns > 0 && isPartidVisible(row.partid),
  );
  const visibleLatest = latest.filter((row) => isPartidVisible(row.partid));
  const protectedPartid = String(targetStimulus?.partid ?? visibleLatest[0]?.partid ?? 0);
  const protectedRow = visibleLatest.find((row) => String(row.partid) === protectedPartid) || visibleLatest[0];
  const bars = protectedRow ? [
    { label: "NoC", value: Number(protectedRow.avg_noc_delay_ns || 0), color: "#4a7a98" },
    { label: "L3", value: Number(protectedRow.avg_cache_delay_ns || 0), color: "#538867" },
    { label: "MC Queue", value: Number(protectedRow.avg_mem_queue_delay_ns || 0), color: "#c17a25" },
    { label: "Service", value: Number(protectedRow.avg_mem_service_delay_ns || 0), color: "#7964a5" },
    { label: "Throttle", value: Number(protectedRow.avg_throttle_delay_ns || 0), color: "#ad4e4e" },
  ] : [];
  drawBarChart($("#delayChart"), bars, {
    xLabel: "延迟来源",
    yLabel: "平均延迟",
    yUnit: "ns",
  });
}

function effectTarget(partid) {
  const config = state.partidConfigs[Number(partid)] || {};
  const stimuli = state.stimulusConfigs.filter(
    (row) => row.enabled && Number(row.partid) === Number(partid),
  );
  const p99Targets = stimuli
    .map((row) => Number(row.target_p99_ns || 0))
    .filter((value) => value > 0);
  const mcCount = Number(
    $('[data-param="memory_controllers"]')?.value || 1,
  );
  return {
    cmin: config.cmin_enable ? Number(config.cmin || 0) : null,
    cmax: config.cmax_enable ? Number(config.cmax || 100) : null,
    bmin: config.bmin_enable
      ? Number(config.bmin_gbps || 0) * mcCount
      : null,
    bmax: config.bmax_enable
      ? Number(config.bmax_gbps || 0) * mcCount
      : null,
    mode: config.limit_mode || "disabled",
    qos: config.mc_qos_enable ? Number(config.mc_qos || 0) : 0,
    p99: p99Targets.length ? Math.min(...p99Targets) : null,
  };
}

function buildEffectRows(partid) {
  const pid = Number(partid);
  const configuredTarget = effectTarget(pid);
  const times = new Set();
  (state.partial.metrics || []).forEach((row) => {
    if (Number(row.partid) === pid) times.add(Number(row.time_ns));
  });
  (state.partial.msc || []).forEach((row) => times.add(Number(row.time_ns)));
  const controls = state.partial.controls || [];
  const sumValues = (values, key, fallback = 0) => values.reduce(
    (sum, row) => sum + Number(row[key] ?? fallback),
    0,
  );
  const sharePercent = (bytes, capacity) => bytes * 100 / Math.max(1, capacity);
  const weightedPercent = (values, key, fallback) => {
    let weighted = 0;
    let capacity = 0;
    values.forEach((row) => {
      const value = Number(row[key]);
      const weight = Number(row.cache_capacity_bytes || 0);
      if (!Number.isFinite(value) || weight <= 0) return;
      weighted += value * weight;
      capacity += weight;
    });
    return capacity > 0 ? weighted / capacity : fallback;
  };
  let previousTime = -1;
  return [...times]
    .filter((timeNs) => timeNs <= state.selectedTime + 1e-9)
    .sort((a, b) => a - b)
    .map((timeNs) => {
      const cacheRows = (state.partial.msc || []).filter(
        (row) => Number(row.time_ns) === timeNs && row.msc_type === "cache",
      );
      const mcRows = (state.partial.msc || []).filter(
        (row) => Number(row.time_ns) === timeNs
          && row.msc_type === "memory_controller",
      );
      const cpuRows = (state.partial.cpu || []).filter(
        (row) => Number(row.time_ns) === timeNs && Number(row.partid) === pid,
      );
      const metric = (state.partial.metrics || []).find(
        (row) => Number(row.time_ns) === timeNs && Number(row.partid) === pid,
      ) || {};
      const cacheValues = cacheRows.map(
        (row) => row.per_partid?.[String(pid)] || {},
      );
      const mcValues = mcRows.map(
        (row) => row.per_partid?.[String(pid)] || {},
      );
      const actualOccupancy = sumValues(cacheValues, "actual_occupancy_bytes");
      const rawOccupancy = sumValues(cacheValues, "raw_occupancy_bytes");
      const filteredOccupancy = cacheValues.reduce(
        (sum, row) => sum + Number(
          row.filtered_occupancy_bytes
          ?? row.estimated_occupancy_bytes
          ?? 0,
        ),
        0,
      );
      const controlOccupancy = cacheValues.reduce(
        (sum, row) => sum + Number(
          row.control_occupancy_bytes
          ?? row.filtered_occupancy_bytes
          ?? row.estimated_occupancy_bytes
          ?? 0,
        ),
        0,
      );
      const cacheCapacity = sumValues(cacheValues, "cache_capacity_bytes");
      const mcRequests = sumValues(mcValues, "requests");
      const mcActualBandwidth = sumValues(mcValues, "achieved_bandwidth_gbps");
      const mcRawBandwidth = sumValues(mcValues, "raw_bandwidth_gbps");
      const mcFilteredBandwidth = sumValues(
        mcValues,
        "filtered_bandwidth_gbps",
      );
      const mcControlBandwidth = mcValues.reduce(
        (sum, row) => sum + Number(
          row.control_bandwidth_gbps
          ?? row.filtered_bandwidth_gbps
          ?? 0,
        ),
        0,
      );
      const hasEffectiveBmin = mcValues.some(
        (row) => row.bmin_gbps != null,
      );
      const hasEffectiveBmax = mcValues.some(
        (row) => row.bmax_gbps != null,
      );
      const effectiveCmin = weightedPercent(
        cacheValues,
        "cmin_percent",
        configuredTarget.cmin,
      );
      const effectiveCmax = weightedPercent(
        cacheValues,
        "cmax_percent",
        configuredTarget.cmax,
      );
      const effectiveBmin = mcValues.reduce(
        (sum, row) => sum + Number(row.bmin_gbps ?? 0),
        0,
      );
      const effectiveBmax = mcValues.reduce(
        (sum, row) => sum + Number(row.bmax_gbps ?? 0),
        0,
      );
      const events = controls.filter(
        (row) => Number(row.partid) === pid
          && Number(row.time_ns) > previousTime
          && Number(row.time_ns) <= timeNs,
      );
      previousTime = timeNs;
      return {
        timeNs,
        l3Share: sharePercent(controlOccupancy, cacheCapacity),
        l3ActualShare: sharePercent(actualOccupancy, cacheCapacity),
        l3RawShare: sharePercent(rawOccupancy, cacheCapacity),
        l3FilteredShare: sharePercent(filteredOccupancy, cacheCapacity),
        l3ControlShare: sharePercent(controlOccupancy, cacheCapacity),
        l3EffectiveCmin: effectiveCmin,
        l3EffectiveCmax: effectiveCmax,
        l3Contended: cacheValues.some(
          (row) => Number(row.allocation_denials || 0) > 0
            || Number(row.cmin_protected_evictions || 0) > 0,
        ),
        mcBandwidth: mcControlBandwidth,
        mcActualBandwidth,
        mcRawBandwidth,
        mcFilteredBandwidth,
        mcControlBandwidth,
        mcEffectiveBmin: hasEffectiveBmin ? effectiveBmin : configuredTarget.bmin,
        mcEffectiveBmax: hasEffectiveBmax ? effectiveBmax : configuredTarget.bmax,
        mcContended: mcRows.some(
          (row) => Number(row.queue_occupancy || 0) > 1
            || Number(row.utilization || 0) > 0.8,
        ),
        baseQos: Math.max(
          0,
          ...mcValues.map((row) => Number(row.base_qos || 0)),
        ),
        effectiveQos: mcValues.reduce(
          (sum, row) => sum
            + Number(row.effective_qos_avg || 0)
            * Number(row.requests || 0),
          0,
        ) / Math.max(1, mcRequests),
        cbusy: Math.max(
          0,
          ...mcValues.map((row) => Number(row.cbusy_level || 0)),
        ),
        outstanding: cpuRows.reduce(
          (sum, row) => sum + Number(row.outstanding || 0),
          0,
        ),
        ostdCap: cpuRows.reduce(
          (sum, row) => sum + Number(
            row.effective_max_outstanding || row.max_outstanding || 0,
          ),
          0,
        ),
        p99: Number(metric.p99_latency_ns || 0),
        throughput: Number(metric.throughput_gbps || 0),
        requests: Number(metric.requests || 0),
        events,
      };
    });
}

function effectState(row, target) {
  if (!row || row.requests <= 0) {
    return { l3: "N/A", bw: "N/A", overall: "无需求" };
  }
  const l3MaxFail = target.cmax != null
    && row.l3Share > target.cmax + 1.0;
  const l3MinFail = target.cmin != null
    && row.l3Contended
    && row.l3Share + 1.0 < target.cmin;
  const bwMaxFail = target.bmax != null
    && target.mode === "hardlimit"
    && row.mcBandwidth > target.bmax * 1.08;
  const bwMinFail = target.bmin != null
    && row.mcContended
    && row.mcBandwidth + 0.5 < target.bmin;
  const l3 = l3MaxFail || l3MinFail
    ? "目标偏离"
    : row.l3Contended ? "机制生效" : "观察";
  const bw = bwMaxFail || bwMinFail
    ? "目标偏离"
    : row.mcContended || target.mode === "hardlimit" ? "机制生效" : "借用";
  return {
    l3,
    bw,
    overall: l3 === "目标偏离" || bw === "目标偏离" ? "需解释" : "机制可观察",
  };
}

function stateBadge(value) {
  const kind = value === "目标偏离" || value === "需解释"
    ? "fail"
    : value === "机制生效" || value === "机制可观察"
      ? "pass"
      : "observe";
  return `<span class="effect-state ${kind}">${escapeHtml(value)}</span>`;
}

function renderControlEffect() {
  syncPartidSelect("#effectPartid", state.effectPartid);
  const selectedRows = buildEffectRows(state.effectPartid);
  const target = effectTarget(state.effectPartid);
  const points = (key) => selectedRows.map(
    (row) => ({ x: row.timeNs, y: Number(row[key] || 0) }),
  );
  const targetSeries = (value) => value == null ? [] : selectedRows.map(
    (row) => ({ x: row.timeNs, y: Number(value) }),
  );
  const rowSeries = (key) => selectedRows
    .filter((row) => row[key] != null)
    .map((row) => ({ x: row.timeNs, y: Number(row[key]) }));
  const eventXs = selectedRows
    .filter((row) => row.events.length)
    .map((row) => row.timeNs);
  const selectedColor = partidColor(state.effectPartid);

  renderLegend("#effectL3Legend", [
    { color: "#60717e", label: "物理实际", kind: "actual" },
    { color: "#a66a00", label: "原始监控", kind: "raw" },
    { color: selectedColor, label: "控制输入", kind: "filtered" },
    { color: "#6d5fa8", label: "最新filtered", kind: "filtered" },
    { color: "#2d7a4c", label: "配置CMIN", kind: "configured" },
    { color: "#2d7a4c", label: "生效CMIN", kind: "effective" },
    { color: "#b43a3a", label: "配置CMAX", kind: "configured" },
    { color: "#b43a3a", label: "生效CMAX", kind: "effective" },
    { color: colors.amber, label: "控制事件", kind: "event" },
  ]);
  drawLineChart($("#effectL3Chart"), [
    { color: "#60717e", width: 1.2, marker: "none", points: points("l3ActualShare") },
    { color: "#a66a00", width: 1.2, dash: [1, 4], marker: "points", points: points("l3RawShare") },
    { color: selectedColor, width: 2.8, points: points("l3ControlShare") },
    { color: "#6d5fa8", width: 1.6, dash: [6, 3], marker: "none", points: points("l3FilteredShare") },
    { color: "#2d7a4c", width: 1.4, dash: [2, 3], marker: "none", points: targetSeries(target.cmin) },
    { color: "#2d7a4c", width: 1.8, dash: [6, 4], step: true, marker: "none", points: rowSeries("l3EffectiveCmin") },
    { color: "#b43a3a", width: 1.4, dash: [2, 3], marker: "none", points: targetSeries(target.cmax) },
    { color: "#b43a3a", width: 1.8, dash: [6, 4], step: true, marker: "none", points: rowSeries("l3EffectiveCmax") },
  ], {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "L3占用比例",
    yUnit: "%",
    yMax: 100,
    eventXs,
  });

  renderLegend("#effectBwLegend", [
    { color: "#60717e", label: "服务实际", kind: "actual" },
    { color: "#a66a00", label: "原始监控", kind: "raw" },
    { color: selectedColor, label: "控制输入", kind: "filtered" },
    { color: "#6d5fa8", label: "最新filtered", kind: "filtered" },
    { color: "#2d7a4c", label: "配置BMIN", kind: "configured" },
    { color: "#2d7a4c", label: "生效BMIN", kind: "effective" },
    { color: "#b43a3a", label: "配置BMAX", kind: "configured" },
    { color: "#b43a3a", label: "生效BMAX", kind: "effective" },
    { color: colors.amber, label: "控制事件", kind: "event" },
  ]);
  drawLineChart($("#effectBwChart"), [
    { color: "#60717e", width: 1.2, marker: "none", points: points("mcActualBandwidth") },
    { color: "#a66a00", width: 1.2, dash: [1, 4], marker: "points", points: points("mcRawBandwidth") },
    { color: selectedColor, width: 2.8, points: points("mcControlBandwidth") },
    { color: "#6d5fa8", width: 1.6, dash: [6, 3], marker: "none", points: points("mcFilteredBandwidth") },
    { color: "#2d7a4c", width: 1.4, dash: [2, 3], marker: "none", points: targetSeries(target.bmin) },
    { color: "#2d7a4c", width: 1.8, dash: [6, 4], step: true, marker: "none", points: rowSeries("mcEffectiveBmin") },
    { color: "#b43a3a", width: 1.4, dash: [2, 3], marker: "none", points: targetSeries(target.bmax) },
    { color: "#b43a3a", width: 1.8, dash: [6, 4], step: true, marker: "none", points: rowSeries("mcEffectiveBmax") },
  ], {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "MC带宽",
    yUnit: "Gbps",
    eventXs,
  });

  renderLegend("#effectQosLegend", [
    { color: "#697680", label: "配置QoS", kind: "configured" },
    { color: selectedColor, label: "生效QoS", kind: "filtered" },
    { color: colors.amber, label: "控制事件", kind: "event" },
  ]);
  drawLineChart($("#effectQosChart"), [
    { color: "#697680", width: 1.4, dash: [2, 3], marker: "none", points: targetSeries(target.qos) },
    { color: selectedColor, width: 2.6, points: points("effectiveQos") },
  ], {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "QoS",
    yUnit: "level",
    yMax: 8,
    eventXs,
  });

  renderLegend("#effectP99Legend", [
    { color: selectedColor, label: "实际P99", kind: "filtered" },
    { color: "#b43a3a", label: "目标P99", kind: "configured" },
    { color: colors.amber, label: "控制事件", kind: "event" },
  ]);
  drawLineChart($("#effectP99Chart"), [
    { color: selectedColor, width: 2.6, points: points("p99") },
    { color: "#b43a3a", width: 1.5, dash: [2, 3], marker: "none", points: targetSeries(target.p99) },
  ], {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "P99延迟",
    yUnit: "ns",
    eventXs,
  });

  const overview = Array.from({ length: 16 }, (_, partid) => {
    const rows = buildEffectRows(partid);
    const latest = rows[rows.length - 1];
    const partidTarget = effectTarget(partid);
    return { partid, latest, target: partidTarget, state: effectState(latest, partidTarget) };
  });
  $("#effectOverviewTable").innerHTML = overview.some((row) => row.latest)
    ? overview.map(({ partid, latest, target: rowTarget, state: rowState }) => `
      <tr>
        <td><span class="partid-chip" style="background:${partidColor(partid)}">${partid}</span></td>
        <td>${rowTarget.cmin == null ? "-" : `${formatNumber(rowTarget.cmin, 1)}%`} / ${rowTarget.cmax == null ? "-" : `${formatNumber(rowTarget.cmax, 1)}%`}</td>
        <td>${latest ? `${formatNumber(latest.l3ControlShare, 2)}% <small>latest ${formatNumber(latest.l3FilteredShare, 2)} / 实际 ${formatNumber(latest.l3ActualShare, 2)}</small>` : "-"}</td>
        <td>${stateBadge(rowState.l3)}</td>
        <td>${rowTarget.bmin == null ? "-" : formatNumber(rowTarget.bmin, 1)} / ${rowTarget.bmax == null ? "-" : formatNumber(rowTarget.bmax, 1)} <small>${escapeHtml(rowTarget.mode)}</small></td>
        <td>${latest ? `${formatNumber(latest.mcControlBandwidth, 3)} Gbps <small>latest ${formatNumber(latest.mcFilteredBandwidth, 3)} / 实际 ${formatNumber(latest.mcActualBandwidth, 3)}</small>` : "-"}</td>
        <td>${stateBadge(rowState.bw)}</td>
        <td>${rowTarget.qos} / ${latest ? formatNumber(latest.effectiveQos, 2) : "-"}</td>
        <td>${rowTarget.p99 == null ? "-" : formatNumber(rowTarget.p99, 1)} / ${latest ? formatNumber(latest.p99, 1) : "-"}</td>
        <td>${stateBadge(rowState.overall)}</td>
      </tr>`).join("")
    : '<tr><td colspan="10" class="empty-cell">运行仿真后显示控制效果</td></tr>';

  $("#effectTimelineTable").innerHTML = selectedRows.length
    ? selectedRows.map((row) => `
      <tr>
        <td>${formatTime(row.timeNs)}</td>
        <td>${formatNumber(row.l3ControlShare, 2)}% <small>latest ${formatNumber(row.l3FilteredShare, 2)} / 原始 ${formatNumber(row.l3RawShare, 2)} / 实际 ${formatNumber(row.l3ActualShare, 2)}</small></td>
        <td>${target.cmin == null ? "-" : `${formatNumber(row.l3EffectiveCmin ?? target.cmin, 1)}%`} / ${target.cmax == null ? "-" : `${formatNumber(row.l3EffectiveCmax ?? target.cmax, 1)}%`} <small>${row.l3Contended ? "替换竞争" : "无替换竞争"}</small></td>
        <td>${formatNumber(row.mcControlBandwidth, 3)} Gbps <small>latest ${formatNumber(row.mcFilteredBandwidth, 3)} / 原始 ${formatNumber(row.mcRawBandwidth, 3)} / 实际 ${formatNumber(row.mcActualBandwidth, 3)}</small></td>
        <td>${target.bmin == null ? "-" : formatNumber(row.mcEffectiveBmin ?? target.bmin, 1)} / ${target.bmax == null ? "-" : formatNumber(row.mcEffectiveBmax ?? target.bmax, 1)} <small>${row.mcContended ? "竞争" : target.mode}</small></td>
        <td>${formatNumber(row.baseQos, 0)} / ${formatNumber(row.effectiveQos, 2)}</td>
        <td>L${row.cbusy} / ${formatNumber(row.outstanding, 0)} of ${formatNumber(row.ostdCap, 0)}</td>
        <td>${formatNumber(row.p99, 2)} ns / ${formatNumber(row.throughput, 3)} Gbps</td>
        <td class="causal-events">${row.events.length ? row.events.map((event) =>
          `<span><b>${escapeHtml(event.target_msc)}</b> ${escapeHtml(event.field)} ${escapeHtml(event.old_value)}→${escapeHtml(event.new_value)}</span>`
        ).join("") : '<span class="muted">无更新</span>'}</td>
      </tr>`).join("")
    : '<tr><td colspan="9" class="empty-cell">选择 PARTID 后显示完整时间线</td></tr>';
}

function formatTargetRange(minValue, maxValue, unit = "") {
  const minText = minValue == null ? "-" : `${formatNumber(minValue, 1)}${unit}`;
  const maxText = maxValue == null ? "-" : `${formatNumber(maxValue, 1)}${unit}`;
  if (minValue == null && maxValue == null) return "未启用";
  return `${minText} ~ ${maxText}`;
}

function overviewMetric(label, value, detail = "") {
  return `
    <div class="overview-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${value}</strong>
      ${detail ? `<small>${detail}</small>` : ""}
    </div>`;
}

function overviewStatus(label, detail = "", kind = "neutral") {
  return `
    <span class="overview-status ${kind}">
      <b>${escapeHtml(label)}</b>
      ${detail ? `<small>${escapeHtml(detail)}</small>` : ""}
    </span>`;
}

function overviewStateKind(value) {
  if (["目标偏离", "需解释", "受限"].includes(value)) return "warn";
  if (["机制生效", "机制可观察", "生效"].includes(value)) return "good";
  if (["借用", "观察", "运行"].includes(value)) return "observe";
  return "neutral";
}

function latestEffectRow(partid) {
  const rows = buildEffectRows(partid);
  return rows[rows.length - 1] || null;
}

function overviewTargetBand(minValue, maxValue, fallbackMax, color) {
  if (minValue == null && maxValue == null) return [];
  return [{
    from: minValue == null ? 0 : Number(minValue),
    to: maxValue == null ? fallbackMax : Number(maxValue),
    color,
  }];
}

function renderControlOverview() {
  syncPartidSelect("#overviewPartid", state.overviewPartid);
  syncOverviewLayerControls();
  const pid = Number(state.overviewPartid);
  const target = effectTarget(pid);
  const rows = buildEffectRows(pid);
  const latest = rows[rows.length - 1] || null;
  const effect = effectState(latest, target);
  const cpu = aggregateCpuResources()[pid] || {};
  const l3 = aggregateL3Resources()[pid] || {};
  const mc = aggregateMcResources()[pid] || {};
  const selectedColor = partidColor(pid);
  const cpuLimited = Number(cpu.cbusyLevel || 0) > 0
    || Number(cpu.effectiveMaxOutstanding || 0) < Number(cpu.maxOutstanding || 0);
  const destinationText = [...(cpu.destinations || new Map()).entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([mcId, values]) => `${mcId}: L${formatNumber(values.cbusy, 0)} cap ${formatNumber(values.limit, 0)}`)
    .join(" / ");

  $("#overviewCpuCard").innerHTML = `
    <div class="overview-status-row">
      ${overviewStatus(cpuLimited ? "源头受限" : "源头放行", destinationText || "无目标MC反馈", cpuLimited ? "warn" : "good")}
    </div>
    <div class="overview-metric-grid">
      ${overviewMetric("Configured OSTD", formatNumber(cpu.maxOutstanding || 0, 0))}
      ${overviewMetric("Effective Cap", formatNumber(cpu.effectiveMaxOutstanding || 0, 0), `CBusy L${formatNumber(cpu.cbusyLevel || 0, 0)}`)}
      ${overviewMetric("Current / Peak", `${formatNumber(cpu.outstanding || 0, 0)} / ${formatNumber(cpu.peakOutstanding || 0, 0)}`)}
      ${overviewMetric("Source Stall", `${formatNumber(cpu.cbusyStallNs || 0, 2)} ns`, `BP ${formatNumber(cpu.backpressureNs || 0, 2)} ns`)}
      ${overviewMetric("Issued / Done", `${formatNumber(cpu.issued || 0, 0)} / ${formatNumber(cpu.completed || 0, 0)}`)}
      ${overviewMetric("Requesters", escapeHtml([...(cpu.requesters || new Set())].join(", ") || "-"))}
    </div>`;

  $("#overviewL3Card").innerHTML = `
    <div class="overview-status-row">
      ${overviewStatus(effect.l3, latest?.l3Contended ? "存在替换压力" : "无替换压力", overviewStateKind(effect.l3))}
    </div>
    <div class="overview-metric-grid">
      ${overviewMetric("CMIN / CMAX", formatTargetRange(target.cmin, target.cmax, "%"))}
      ${overviewMetric("Control Input", latest ? `${formatNumber(latest.l3ControlShare, 2)}%` : "--", "锁存读取值")}
      ${overviewMetric("Latest Filtered", latest ? `${formatNumber(latest.l3FilteredShare, 2)}%` : "--", "最新发布")}
      ${overviewMetric("Physical Actual", latest ? `${formatNumber(latest.l3ActualShare, 2)}%` : "--", "验证误差")}
      ${overviewMetric("Allocation Denial", formatNumber(l3.allocationDenials || 0, 0))}
      ${overviewMetric("Hit Rate", `${((l3.hitRate || 0) * 100).toFixed(2)}%`)}
    </div>`;

  $("#overviewMcCard").innerHTML = `
    <div class="overview-status-row">
      ${overviewStatus(effect.bw, mc.hardBlock ? "hard block" : mc.overBmax ? "over BMAX" : mc.underBmin ? "under BMIN" : "当前区间", overviewStateKind(effect.bw))}
    </div>
    <div class="overview-metric-grid">
      ${overviewMetric("BMIN / BMAX", formatTargetRange(target.bmin, target.bmax, " Gbps"), escapeHtml(target.mode || "disabled"))}
      ${overviewMetric("Control Input", latest ? `${formatNumber(latest.mcControlBandwidth, 3)} Gbps` : "--", "锁存读取值")}
      ${overviewMetric("Latest Filtered", latest ? `${formatNumber(latest.mcFilteredBandwidth, 3)} Gbps` : "--", "最新发布")}
      ${overviewMetric("Service Actual", latest ? `${formatNumber(latest.mcActualBandwidth, 3)} Gbps` : "--", "实际服务")}
      ${overviewMetric("Buffer / Queue", formatNumber(mc.bufferEntries || 0, 0), `${formatNumber(mc.avgQueueDelayNs || 0, 2)} ns avg`)}
      ${overviewMetric("QoS Base / Eff", `${escapeHtml(mc.qos ?? "-")} / ${formatNumber(mc.effectiveQos || 0, 2)}`)}
    </div>`;

  const pointSeries = (key) => rows.map(
    (row) => ({ x: row.timeNs, y: Number(row[key] || 0) }),
  );
  const eventXs = overviewLayerEnabled("events")
    ? rows.filter((row) => row.events.length).map((row) => row.timeNs)
    : [];
  const l3Series = [
    ...(overviewLayerEnabled("actual")
      ? [{ color: "#697680", width: 1.2, marker: "none", points: pointSeries("l3ActualShare") }]
      : []),
    ...(overviewLayerEnabled("raw")
      ? [{
        color: "#a66a00",
        width: 1.1,
        dash: [1, 4],
        marker: "points",
        points: pointSeries("l3RawShare"),
      }]
      : []),
    ...(overviewLayerEnabled("controlInput")
      ? [{ color: selectedColor, width: 3, points: pointSeries("l3ControlShare") }]
      : []),
    ...(overviewLayerEnabled("filtered")
      ? [{ color: "#6d5fa8", width: 1.8, dash: [6, 3], points: pointSeries("l3FilteredShare") }]
      : []),
  ];
  renderLegend("#overviewL3Legend", [
    ...(overviewLayerEnabled("targetBand") ? [{ color: "#2d7a4c", label: "目标带", kind: "band" }] : []),
    ...(overviewLayerEnabled("controlInput") ? [{ color: selectedColor, label: "control input", kind: "filtered" }] : []),
    ...(overviewLayerEnabled("filtered") ? [{ color: "#6d5fa8", label: "latest filtered", kind: "filtered" }] : []),
    ...(overviewLayerEnabled("actual") ? [{ color: "#697680", label: "actual", kind: "actual" }] : []),
    ...(overviewLayerEnabled("raw") ? [{ color: "#a66a00", label: "raw", kind: "raw" }] : []),
    ...(overviewLayerEnabled("events") ? [{ color: colors.amber, label: "控制事件", kind: "event" }] : []),
  ]);
  drawLineChart($("#overviewL3Chart"), l3Series, {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "L3占用比例",
    yUnit: "%",
    yMax: 100,
    eventXs,
    bands: overviewLayerEnabled("targetBand")
      ? overviewTargetBand(target.cmin, target.cmax, 100, "rgba(45, 122, 76, 0.14)")
      : [],
  });

  const mcValues = rows.flatMap((row) => [
    Number(row.mcActualBandwidth || 0),
    Number(row.mcControlBandwidth || 0),
    Number(row.mcFilteredBandwidth || 0),
    Number(row.mcRawBandwidth || 0),
  ]);
  const mcYMax = Math.max(
    1,
    ...mcValues,
    Number(target.bmin || 0),
    Number(target.bmax || 0),
  ) * 1.15;
  const mcSeries = [
    ...(overviewLayerEnabled("actual")
      ? [{ color: "#697680", width: 1.2, marker: "none", points: pointSeries("mcActualBandwidth") }]
      : []),
    ...(overviewLayerEnabled("raw")
      ? [{
        color: "#a66a00",
        width: 1.1,
        dash: [1, 4],
        marker: "points",
        points: pointSeries("mcRawBandwidth"),
      }]
      : []),
    ...(overviewLayerEnabled("controlInput")
      ? [{ color: selectedColor, width: 3, points: pointSeries("mcControlBandwidth") }]
      : []),
    ...(overviewLayerEnabled("filtered")
      ? [{ color: "#6d5fa8", width: 1.8, dash: [6, 3], points: pointSeries("mcFilteredBandwidth") }]
      : []),
  ];
  renderLegend("#overviewMcLegend", [
    ...(overviewLayerEnabled("targetBand") ? [{ color: "#2d7a4c", label: "目标带", kind: "band" }] : []),
    ...(overviewLayerEnabled("controlInput") ? [{ color: selectedColor, label: "control input", kind: "filtered" }] : []),
    ...(overviewLayerEnabled("filtered") ? [{ color: "#6d5fa8", label: "latest filtered", kind: "filtered" }] : []),
    ...(overviewLayerEnabled("actual") ? [{ color: "#697680", label: "actual", kind: "actual" }] : []),
    ...(overviewLayerEnabled("raw") ? [{ color: "#a66a00", label: "raw", kind: "raw" }] : []),
    ...(overviewLayerEnabled("events") ? [{ color: colors.amber, label: "控制事件", kind: "event" }] : []),
  ]);
  drawLineChart($("#overviewMcChart"), mcSeries, {
    xLabel: "时间",
    xUnit: "ns",
    yLabel: "MC带宽",
    yUnit: "Gbps",
    yMax: mcYMax,
    eventXs,
    bands: overviewLayerEnabled("targetBand")
      ? overviewTargetBand(target.bmin, target.bmax, mcYMax, "rgba(45, 122, 76, 0.14)")
      : [],
  });

  const cpuRows = aggregateCpuResources();
  const l3Rows = aggregateL3Resources();
  const mcRows = aggregateMcResources();
  $("#overviewPartidMatrix").innerHTML = Array.from({ length: 16 }, (_, partid) => {
    const row = latestEffectRow(partid);
    const rowTarget = effectTarget(partid);
    const rowState = effectState(row, rowTarget);
    const cpuRow = cpuRows[partid] || {};
    const l3Row = l3Rows[partid] || {};
    const mcRow = mcRows[partid] || {};
    const cpuLabel = Number(cpuRow.cbusyLevel || 0) > 0
      ? `L${formatNumber(cpuRow.cbusyLevel, 0)}`
      : Number(cpuRow.outstanding || 0) > 0 ? "运行" : "空闲";
    return `
      <button type="button" class="overview-partid ${partid === pid ? "active" : ""}" data-overview-partid="${partid}" style="--partid-color:${partidColor(partid)}">
        <b>ID ${partid}</b>
        <span class="${overviewStateKind(cpuLabel)}">CPU ${escapeHtml(cpuLabel)}</span>
        <span class="${overviewStateKind(rowState.l3)}">L3 ${escapeHtml(rowState.l3)}</span>
        <span class="${overviewStateKind(rowState.bw)}">MC ${escapeHtml(rowState.bw)}</span>
        <small>${formatNumber(l3Row.allocationDenials || 0, 0)} deny · ${formatNumber(mcRow.hardBlocks || 0, 0)} hard</small>
      </button>`;
  }).join("");
}

function renderPartidTable() {
  const rows = latestBy(state.partial.metrics, "partid")
    .filter((row) => isPartidVisible(row.partid));
  $("#partidTable").innerHTML = rows.length ? rows.map((row) => `
    <tr>
      <td><span class="partid-dot" style="background:${partidColor(row.partid)}"></span> ${escapeHtml(row.partid)}</td>
      <td>${formatNumber(row.throughput_gbps, 2)}</td>
      <td>${formatNumber(row.p99_latency_ns, 2)}</td>
      <td>${(Number(row.cache_hit_rate || 0) * 100).toFixed(2)}%</td>
      <td>${formatNumber(row.avg_mem_queue_delay_ns, 2)}</td>
      <td>${formatNumber(row.avg_throttle_delay_ns, 2)}</td>
    </tr>`).join("") : '<tr><td colspan="6" class="empty-cell">尚无仿真结果</td></tr>';
}

function renderMscTable() {
  const rows = latestBy(state.partial.msc, "msc_id");
  $("#mscTable").innerHTML = rows.length ? rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.msc_id)}</td>
      <td>${escapeHtml(row.msc_type)}</td>
      <td>${(Number(row.utilization || 0) * 100).toFixed(1)}%</td>
      <td>${formatNumber(row.queue_occupancy, 2)}</td>
      <td>${formatNumber(row.requests, 0)}</td>
      <td>${formatNumber(row.bytes, 0)}</td>
    </tr>`).join("") : '<tr><td colspan="6" class="empty-cell">尚无仿真结果</td></tr>';
}

function renderControlTable() {
  const rows = visibleRows(state.partial.controls)
    .filter((row) => isPartidVisible(row.partid))
    .slice()
    .reverse();
  $("#controlTable").innerHTML = rows.length ? rows.map((row) => `
    <tr>
      <td>${formatNumber(row.time_ns, 0)}</td>
      <td>${escapeHtml(row.target_msc)}</td>
      <td>${escapeHtml(row.partid)}</td>
      <td>${escapeHtml(row.field)}</td>
      <td>${escapeHtml(row.old_value)}</td>
      <td>${escapeHtml(row.new_value)}</td>
      <td>${escapeHtml(row.reason)}</td>
    </tr>`).join("") : '<tr><td colspan="7" class="empty-cell">暂无控制更新</td></tr>';
}

function aggregateMpamMonitors() {
  const rows = latestBy(state.partial.msc, "msc_id");
  const result = Array.from({ length: 16 }, (_, partid) => ({
    partid,
    l3Bandwidth: 0,
    l3Occupancy: 0,
    sampledWays: 0,
    cmin: 0,
    cmax: 0,
    cpbm: "",
    mcBandwidth: 0,
    bmin: 0,
    bmax: 0,
    mode: "",
    softRequests: 0,
    hardBlocks: 0,
  }));
  rows.forEach((row) => {
    const perPartid = row.per_partid || {};
    Object.entries(perPartid).forEach(([pidText, values]) => {
      const pid = Number(pidText);
      if (!Number.isInteger(pid) || pid < 0 || pid > 15) return;
      const target = result[pid];
      if (row.msc_type === "cache") {
        target.l3Bandwidth += Number(values.estimated_bandwidth_gbps || 0);
        target.l3Occupancy += Number(values.estimated_occupancy_bytes || 0);
        target.sampledWays += Number(values.sampled_way_count || 0);
        target.cmin = Number(values.cmin || 0);
        target.cmax = Number(values.cmax || 0);
        target.cpbm = values.cpbm ?? target.cpbm;
      } else if (row.msc_type === "memory_controller") {
        target.mcBandwidth += Number(values.achieved_bandwidth_gbps || 0);
        target.bmin += Number(values.bmin_gbps || 0);
        target.bmax += Number(values.bmax_gbps || 0);
        target.mode = values.limit_mode || target.mode;
        target.softRequests += Number(values.softlimit_requests || 0);
        target.hardBlocks += Number(values.hardlimit_block_events || 0);
      }
    });
  });
  return result;
}

function renderMpamMonitorTable() {
  const hasData = visibleRows(state.partial.msc).length > 0;
  const rows = aggregateMpamMonitors()
    .filter((row) => isPartidVisible(row.partid));
  $("#mpamMonitorTable").innerHTML = hasData && rows.length ? rows.map((row) => `
    <tr>
      <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
      <td>${formatNumber(row.l3Bandwidth, 3)}</td>
      <td>${formatNumber(row.l3Occupancy, 0)}</td>
      <td>${formatNumber(row.sampledWays, 0)}</td>
      <td>${row.cmin}</td>
      <td>${row.cmax}</td>
      <td><code>${escapeHtml(row.cpbm || "-")}</code></td>
      <td>${formatNumber(row.mcBandwidth, 3)}</td>
      <td>${formatNumber(row.bmin, 1)}</td>
      <td>${formatNumber(row.bmax, 1)}</td>
      <td>${escapeHtml(row.mode || "-")}</td>
      <td>${formatNumber(row.softRequests, 0)}</td>
      <td>${formatNumber(row.hardBlocks, 0)}</td>
    </tr>
  `).join("") : '<tr><td colspan="13" class="empty-cell">尚无 MPAM 监控结果</td></tr>';
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

let activeHelpTarget = null;

function setHelp(target, text) {
  if (!target || !text) return;
  target.dataset.help = text;
  target.removeAttribute("title");
  target.setAttribute("aria-describedby", "helpTooltip");
  bindHelpTarget(target);
}

function applyContextHelp() {
  $$("[data-param]").forEach((input) => {
    setConfigHelp(
      input.closest("label") || input,
      "parameters",
      input.dataset.param,
      input.type === "radio" ? input.value : input.value,
    );
  });
  Object.entries(configHeaderFields).forEach(([group, fields]) => {
    const tableSelector = group === "stimulus"
      ? ".stimulus-config-table"
      : ".mpam-config-table";
    $$(`${tableSelector} th`).forEach((header) => {
      const key = fields[header.textContent.trim()];
      if (key) setConfigHelp(header, group, key);
    });
  });
  $$("th").forEach((header) => {
    if (!header.dataset.configKey && !header.dataset.algorithm) {
      setHelp(header, headerHelp[header.textContent.trim()]);
    }
  });
  $$(".result-tab").forEach((button) => {
    setHelp(button, resultTabHelp[button.textContent.trim()]);
  });
  $$(".config-section h2").forEach((heading) => {
    setHelp(heading, sectionHeadingHelp[heading.textContent.trim()]);
  });
  const chartHelp = {
    "P99 延迟": "每个 PARTID 在各采样周期内完成请求的 99 分位总延迟。",
    "有效带宽": "每个 PARTID 在采样周期内完成字节换算的有效带宽。",
    "MSC 队列占用": "NoC、L3、MC 组件报告的平均队列 entries；L3 当前没有显式请求队列。",
    "延迟分解": "选择一个受保护 PARTID，展示 NoC、L3、MC 排队、服务和限速平均延迟。",
  };
  $$(".chart-title h3").forEach((heading) => {
    setHelp(heading, chartHelp[heading.textContent.trim()]);
  });
  const flowHelp = {
    PE: "硬件线程 requester 产生带 PARTID/PMG 的抽象请求，并受 outstanding 限制。",
    NoC: "建模固定跳延迟、链路序列化、队列和基于优先级的仲裁。",
    L3: "按 PARTID 应用 CPBM/CMIN/CMAX，并以 8-set 抽样估算占用。",
    MC: "按 PARTID 应用 BMIN/BMAX token/credit 并统计 PMG 带宽。",
    Scheduler: "在竞争请求间组合 priority、BMIN bonus、soft penalty 和 aging。",
    Monitor: "按控制周期采集 PARTID 与 PARTID+PMG 指标供软件查看和闭环决策。",
  };
  $$(".flow-stage").forEach((stage) => {
    if (!stage.dataset.algorithm) {
      setHelp(stage, flowHelp[stage.querySelector("b")?.textContent.trim()]);
    }
  });
  $$("[data-help]").forEach(bindHelpTarget);
  auditConfigHelpCoverage();
}

let algorithmTimer = null;
let algorithmTarget = null;
let algorithmPinned = false;

function positionAlgorithmPopover(target) {
  const popover = $("#algorithmPopover");
  popover.style.maxHeight = "";
  const anchor = target.getBoundingClientRect();
  let box = popover.getBoundingClientRect();
  const gap = 10;
  const rightSpace = window.innerWidth - anchor.right - 12;
  const leftSpace = anchor.left - 12;
  let left;
  let top;
  if (rightSpace >= box.width + gap) {
    left = anchor.right + gap;
    top = Math.max(12, anchor.top);
  } else if (leftSpace >= box.width + gap) {
    left = anchor.left - box.width - gap;
    top = Math.max(12, anchor.top);
  } else {
    left = Math.max(
      12,
      Math.min(anchor.left, window.innerWidth - box.width - 12),
    );
    const below = window.innerHeight - anchor.bottom - 12;
    const above = anchor.top - 12;
    const useBelow = below >= above;
    const available = Math.max(160, (useBelow ? below : above) - gap);
    popover.style.maxHeight = `${available}px`;
    box = popover.getBoundingClientRect();
    top = useBelow
      ? anchor.bottom + gap
      : Math.max(12, anchor.top - box.height - gap);
  }
  if (top + box.height > window.innerHeight - 12) {
    top = Math.max(12, window.innerHeight - box.height - 12);
  }
  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
}

function showAlgorithmPopover(target, pin = false) {
  const entry = algorithmHelp[target?.dataset.algorithm];
  if (!entry) return;
  clearTimeout(algorithmTimer);
  hideHelp();
  algorithmTarget = target;
  algorithmPinned = pin;
  $("#algorithmPopoverTitle").textContent = entry.title;
  $("#algorithmPopoverBody").innerHTML = renderAlgorithmBody(entry);
  const popover = $("#algorithmPopover");
  popover.classList.add("visible");
  popover.setAttribute("aria-hidden", "false");
  requestAnimationFrame(() => positionAlgorithmPopover(target));
}

function renderAlgorithmBody(entry) {
  if (entry.body) {
    return `<p class="algorithm-compact-lines">${escapeHtml(entry.body)}</p>`;
  }
  const labels = {
    summary: "功能",
    inputs: "输入",
    state: "保存状态",
    cadence: "更新周期",
    decision: "决策规则",
    action: "动作点",
    recovery: "恢复",
    priority: "交互优先级",
    forward_progress: "前向进展",
    evidence: "可观察证据",
    boundary: "模型边界",
  };
  const lines = Object.entries(labels)
    .filter(([key]) => entry[key])
    .map(([key, label]) => `${label}：${entry[key]}`);
  return `<p class="algorithm-compact-lines">${escapeHtml(lines.join("\n"))}</p>`;
}

function scheduleAlgorithmPopover(target) {
  clearTimeout(algorithmTimer);
  algorithmTimer = setTimeout(
    () => showAlgorithmPopover(target, false),
    250,
  );
}

function hideAlgorithmPopover(force = false) {
  clearTimeout(algorithmTimer);
  if (algorithmPinned && !force) return;
  algorithmPinned = false;
  algorithmTarget = null;
  $("#algorithmPopover").classList.remove("visible");
  $("#algorithmPopover").setAttribute("aria-hidden", "true");
}

function bindAlgorithmEvents() {
  document.addEventListener("mouseover", (event) => {
    const target = event.target.closest?.("[data-algorithm]");
    if (target && target !== algorithmTarget && !algorithmPinned) {
      scheduleAlgorithmPopover(target);
    }
  });
  document.addEventListener("mouseout", (event) => {
    const target = event.target.closest?.("[data-algorithm]");
    if (
      target
      && !target.contains(event.relatedTarget)
      && !$("#algorithmPopover").contains(event.relatedTarget)
      && !algorithmPinned
    ) {
      hideAlgorithmPopover();
    }
  });
  document.addEventListener("click", (event) => {
    const target = event.target.closest?.("[data-algorithm]");
    if (target) showAlgorithmPopover(target, true);
  });
  document.addEventListener("focusin", (event) => {
    const target = event.target.closest?.("[data-algorithm]");
    if (target && target !== algorithmTarget) {
      showAlgorithmPopover(target, false);
    }
  });
  document.addEventListener("focusout", (event) => {
    const target = event.target.closest?.("[data-algorithm]");
    if (
      target
      && !target.contains(event.relatedTarget)
      && !$("#algorithmPopover").contains(event.relatedTarget)
      && !algorithmPinned
    ) {
      hideAlgorithmPopover();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") hideAlgorithmPopover(true);
  });
  $("#algorithmPopover").addEventListener("mouseleave", () => {
    if (!algorithmPinned) hideAlgorithmPopover();
  });
  $("#algorithmPopoverClose").addEventListener(
    "click",
    (event) => {
      event.stopPropagation();
      hideAlgorithmPopover(true);
    },
  );
}

function positionHelp(target) {
  const tooltip = $("#helpTooltip");
  const anchor = target.getBoundingClientRect();
  const box = tooltip.getBoundingClientRect();
  const gap = 8;
  const rightSpace = window.innerWidth - anchor.right - 12;
  const leftSpace = anchor.left - 12;
  let left;
  let top;
  if (rightSpace >= box.width + gap) {
    left = anchor.right + gap;
    top = Math.max(12, anchor.top);
  } else if (leftSpace >= box.width + gap) {
    left = anchor.left - box.width - gap;
    top = Math.max(12, anchor.top);
  } else {
    left = Math.max(
      12,
      Math.min(anchor.left, window.innerWidth - box.width - 12),
    );
    const below = window.innerHeight - anchor.bottom - 12;
    const above = anchor.top - 12;
    top = below >= box.height || below >= above
      ? anchor.bottom + gap
      : Math.max(12, anchor.top - box.height - gap);
  }
  if (top + box.height > window.innerHeight - 12) {
    top = Math.max(12, window.innerHeight - box.height - 12);
  }
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function showHelp(target) {
  if (!target?.dataset.help) return;
  if (target.closest?.("[data-algorithm]")) return;
  activeHelpTarget = target;
  const tooltip = $("#helpTooltip");
  tooltip.textContent = target.dataset.help;
  tooltip.classList.add("visible");
  requestAnimationFrame(() => positionHelp(target));
}

function hideHelp(target) {
  if (target && target !== activeHelpTarget) return;
  activeHelpTarget = null;
  $("#helpTooltip").classList.remove("visible");
}

function bindHelpTarget(target) {
  if (!target) return;
  // Avoid showing the browser's native title bubble over the custom tooltip.
  target.removeAttribute("title");
  if (target.dataset.helpBound === "true") return;
  target.dataset.helpBound = "true";
  target.addEventListener("mouseenter", () => showHelp(target));
  target.addEventListener("mouseleave", () => hideHelp(target));
  target.addEventListener("focusin", () => showHelp(target));
  target.addEventListener("focusout", () => hideHelp(target));
}

function bindHelpEvents() {
  document.addEventListener("mouseover", (event) => {
    const target = event.target.closest?.("[data-help]");
    if (target && target !== activeHelpTarget) showHelp(target);
  });
  document.addEventListener("mouseout", (event) => {
    const target = event.target.closest?.("[data-help]");
    if (
      target
      && !target.contains(event.relatedTarget)
    ) hideHelp(target);
  });
  document.addEventListener("focusin", (event) => {
    const target = event.target.closest?.("[data-help]");
    if (target) showHelp(target);
  });
  document.addEventListener("focusout", (event) => {
    const target = event.target.closest?.("[data-help]");
    if (target) hideHelp(target);
  });
}

function auditConfigHelpCoverage() {
  const controls = $$(
    "#configForm input, #configForm select, #configForm textarea",
  );
  const missing = controls.filter(
    (control) => !control.closest("[data-help], [data-algorithm]"),
  );
  controls.forEach((control) => {
    control.toggleAttribute("data-help-missing", missing.includes(control));
  });
  if (missing.length) {
    console.error(
      "Configuration help metadata missing:",
      missing.map((control) =>
        control.dataset.param
        || control.dataset.field
        || control.dataset.stimulusField
        || control.name
        || control.id
      ),
    );
  }
  return missing;
}

function refreshChangedConfigHelp(control) {
  const target = control.closest?.("[data-config-group]");
  if (!target) return;
  setConfigHelp(
    target,
    target.dataset.configGroup,
    target.dataset.configKey,
    control.value,
  );
}

function togglePlayback() {
  if (!state.result) return;
  if (state.playing) {
    stopPlayback();
    return;
  }
  state.playing = true;
  $("#playButton").textContent = "Ⅱ";
  const maxTime = state.result.summary.simulation_time_ns;
  if (state.selectedTime >= maxTime) state.selectedTime = 0;
  const step = Math.max(1, maxTime / 60);
  state.playTimer = setInterval(() => {
    state.selectedTime = Math.min(maxTime, state.selectedTime + step);
    syncTimeline();
    renderAll();
    if (state.selectedTime >= maxTime) stopPlayback();
  }, 90);
}

function stopPlayback() {
  state.playing = false;
  clearInterval(state.playTimer);
  $("#playButton").textContent = "▶";
}

const advancedEvidenceViews = [
  "resource-monitor",
  "control-effect",
  "monitor-group",
  "mpam-monitor",
  "partid",
  "msc",
  "controls",
  "experiment",
  "verification",
];

function setupAdvancedEvidence() {
  const body = $("#advancedEvidenceBody");
  if (!body) return;
  advancedEvidenceViews.forEach((name) => {
    const view = document.querySelector(`[data-result-view="${name}"]`);
    if (!view || view.classList.contains("advanced-panel")) return;
    view.classList.remove("result-view", "active");
    view.classList.add("advanced-panel");
    view.dataset.advancedPanel = name;
    body.appendChild(view);
  });
  activateAdvancedEvidence(state.advancedEvidenceView);
}

function activateAdvancedEvidence(name) {
  state.advancedEvidenceView = name;
  $$(".advanced-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.advancedTarget === name);
  });
  $$(".advanced-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.advancedPanel === name);
  });
  if (name === "resource-monitor") renderResourceMonitor();
  if (name === "control-effect") {
    renderControlEffect();
    requestAnimationFrame(renderControlEffect);
  }
  if (name === "experiment") renderExperiment();
  if (name === "verification") renderControlVerification();
}

function bindEvents() {
  bindHelpEvents();
  bindAlgorithmEvents();
  setupAdvancedEvidence();
  $$(".tab-button").forEach((button) => button.addEventListener("click", () => {
    $$(".tab-button").forEach((node) => node.classList.toggle("active", node === button));
    $$(".config-section").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab));
    $("#configForm").scrollLeft = 0;
    $(".workspace").classList.toggle(
      "config-wide",
      button.dataset.tab === "mpam"
      || button.dataset.tab === "traffic"
      || button.dataset.tab === "resctrl",
    );
  }));
  $$(".result-tab").forEach((button) => button.addEventListener("click", () => {
    activateResultTab(button.dataset.resultTab);
    if (button.dataset.resultTab === "control-overview") renderControlOverview();
    if (button.dataset.resultTab === "causal") renderCausalTimeline();
    if (button.dataset.resultTab === "advanced-evidence") {
      activateAdvancedEvidence(state.advancedEvidenceView);
    }
  }));
  $$(".advanced-tab").forEach((button) => button.addEventListener("click", () => {
    activateAdvancedEvidence(button.dataset.advancedTarget);
  }));
  $$(".resource-tab").forEach((button) => button.addEventListener("click", () => {
    state.resourceView = button.dataset.resourceView;
    $$(".resource-tab").forEach((node) => node.classList.toggle("active", node === button));
    renderResourceMonitor();
  }));
  $("#partidVisibility").addEventListener("change", (event) => {
    const input = event.target.closest?.("[data-visible-partid]");
    if (!input) return;
    const partid = Number(input.dataset.visiblePartid);
    if (input.checked) state.visiblePartids.add(partid);
    else state.visiblePartids.delete(partid);
    renderAll();
  });
  $("#selectAllPartids").addEventListener("click", () => {
    state.visiblePartids = new Set(Array.from({ length: 16 }, (_, partid) => partid));
    renderAll();
  });
  $("#clearAllPartids").addEventListener("click", () => {
    state.visiblePartids = new Set();
    renderAll();
  });
  $$('input[name="policy"]').forEach((input) => input.addEventListener("change", renderResourceMonitor));
  $("#presetSelect").addEventListener("change", updatePresetSummary);
  $("#applyPresetButton").addEventListener("click", applySelectedPreset);
  $("#runButton").addEventListener("click", runSimulation);
  $("#experimentButton").addEventListener("click", runExperiment);
  $("#controlVerificationButton").addEventListener(
    "click",
    runControlVerification,
  );
  $("#experimentPartid").addEventListener("change", (event) => {
    state.experimentPartid = Number(event.target.value);
    renderExperiment();
  });
  $("#causalPartid").addEventListener("change", (event) => {
    state.causalPartid = Number(event.target.value);
    renderCausalTimeline();
  });
  $("#effectPartid").addEventListener("change", (event) => {
    state.effectPartid = Number(event.target.value);
    renderControlEffect();
  });
  $("#overviewPartid").addEventListener("change", (event) => {
    state.overviewPartid = Number(event.target.value);
    renderControlOverview();
  });
  $("#overviewChartLayers").addEventListener("change", (event) => {
    const input = event.target.closest?.("[data-overview-layer]");
    if (!input) return;
    state.overviewChartLayers[input.dataset.overviewLayer] = input.checked;
    renderControlOverview();
  });
  $("#overviewPartidMatrix").addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-overview-partid]");
    if (!button) return;
    state.overviewPartid = Number(button.dataset.overviewPartid);
    renderControlOverview();
  });
  $("#resetButton").addEventListener("click", () => {
    fillForm(state.defaults);
    renderConfigDiagnostics();
  });
  $("#resetPartidButton").addEventListener("click", () => {
    renderPartidConfig(state.defaults.partid_configs || []);
    normalizePartidMasks();
    normalizeCbusyCaps();
    applyContextHelp();
    renderConfigDiagnostics();
  });
  $("#resetStimulusButton").addEventListener("click", () => {
    renderStimulusConfig(state.defaults.stimulus_configs || []);
    applyContextHelp();
    renderConfigDiagnostics();
  });
  $("#resetResctrlButton").addEventListener("click", () => {
    renderResctrlConfig(state.defaults.resctrl_groups || []);
    applyContextHelp();
    renderConfigDiagnostics();
  });
  $("#addResctrlGroupButton").addEventListener("click", addResctrlGroup);
  $("#resctrlGroupTable").addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-remove-resctrl]");
    if (!button) return;
    const index = Number(button.dataset.removeResctrl);
    const groups = collectResctrlGroups();
    groups.splice(index, 1);
    renderResctrlConfig(groups);
    applyContextHelp();
    renderConfigDiagnostics();
  });
  $("#playButton").addEventListener("click", togglePlayback);
  $("#timeSlider").addEventListener("input", (event) => {
    stopPlayback();
    state.selectedTime = Number(event.target.value);
    $("#timeOutput").textContent = formatTime(state.selectedTime);
    renderAll();
  });
  $('[data-param="duration_ns"]').addEventListener("input", clampDependentInputs);
  $('[data-param="max_outstanding"]').addEventListener("input", normalizeCbusyCaps);
  $('[data-param="l3_ways"]').addEventListener("input", normalizePartidMasks);
  $("#partidConfigTable").addEventListener("change", (event) => {
    if (event.target.matches('[data-field="cpbm"], [data-field="cmin"], [data-field="cmax"]')) {
      normalizePartidMasks();
    }
    if (event.target.matches(
      '[data-field="cbusy_l1_ostd"], [data-field="cbusy_l2_ostd"], [data-field="cbusy_l3_ostd"]',
    )) {
      normalizeCbusyCaps();
    }
  });
  $("#configForm").addEventListener("input", renderConfigDiagnostics);
  $("#configForm").addEventListener("change", (event) => {
    refreshChangedConfigHelp(event.target);
    renderConfigDiagnostics();
  });
  window.addEventListener("resize", () => requestAnimationFrame(() => {
    renderCharts();
    if (
      document.querySelector('.result-view.active')?.dataset.resultView
      === "control-overview"
    ) {
      renderControlOverview();
    }
    if (
      document.querySelector('.result-view.active')?.dataset.resultView
      === "advanced-evidence"
      && state.advancedEvidenceView === "control-effect"
    ) {
      renderControlEffect();
    }
  }));
}

async function init() {
  bindEvents();
  try {
    await loadDefaults();
    applyContextHelp();
    setStatus("ready", "调整参数后运行仿真", 0);
    renderConfigDiagnostics();
    renderAll();
  } catch (error) {
    failRun(error.message);
  }
}

init();
