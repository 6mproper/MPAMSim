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
  resourceView: "cpu",
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
    PID: "partid",
    PMG: "pmg",
    Type: "workload_type",
    Rate: "rate_value",
    Unit: "rate_unit",
    Bytes: "request_size_bytes",
    Read: "read_ratio",
    "WSS MB": "working_set_mb",
    "P99 ns": "target_p99_ns",
  },
  partid: {
    PID: "partid",
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
  "Core Pool / P OSTD": "该 PARTID 所在 Core 的共享池总占用/峰值/上限，以及 Core 内该 PARTID 的合计占用；共享池总占用包含其他 PARTID。",
  "Home MC P OSTD": "按目标 MC 分开的 Core/PARTID outstanding、周期峰值、有效 CBusy cap 与等级；MC0 的反馈不限制发往 MC1 的请求。",
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
  "Physical / Raw / Filtered": "Physical来自全部真实set/tag/way；Raw来自每8个set首set owner并按8倍缩放；Filtered是CMIN/CMAX实际读取的递归滤波MPAM值。",
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
  $$("[data-param]").forEach((input) => {
    const key = input.dataset.param;
    if (!(key in values)) return;
    if (input.type === "radio") input.checked = input.value === String(values[key]);
    else if (input.type === "checkbox") input.checked = Boolean(values[key]);
    else input.value = values[key];
  });
  clampDependentInputs();
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
    (_, partid) => [partid, `P${partid}`],
  );
  const typeOptions = [
    ["stream", "stream"],
    ["pointer_chase", "pointer"],
    ["random_read", "random"],
    ["mixed_rw", "mixed"],
    ["bursty_dma", "burst"],
  ];
  $("#stimulusConfigTable").innerHTML = state.stimulusConfigs.map((row) => `
    <tr data-stimulus-row="${row.slot}">
      <td><span class="thread-chip">${escapeHtml(row.requester)}</span></td>
      <td><input data-stimulus-field="enabled" ${configHelpAttributes("stimulus", "enabled")} type="checkbox" ${row.enabled ? "checked" : ""}></td>
      <td><select data-stimulus-field="partid" ${configHelpAttributes("stimulus", "partid", row.partid)}>${selectOptions(partidOptions, row.partid)}</select></td>
      <td><input data-stimulus-field="pmg" ${configHelpAttributes("stimulus", "pmg")} type="number" min="0" max="15" step="1" value="${row.pmg}"></td>
      <td><select data-stimulus-field="workload_type" ${configHelpAttributes("stimulus", "workload_type", row.workload_type)}>${selectOptions(typeOptions, row.workload_type)}</select></td>
      <td><input data-stimulus-field="rate_value" ${configHelpAttributes("stimulus", "rate_value")} type="number" min="0" max="4096" step="0.1" value="${row.rate_value}"></td>
      <td><select data-stimulus-field="rate_unit" ${configHelpAttributes("stimulus", "rate_unit", row.rate_unit)}>${selectOptions([["gbps", "Gbps"], ["mrps", "MRPS"]], row.rate_unit)}</select></td>
      <td><input data-stimulus-field="request_size_bytes" ${configHelpAttributes("stimulus", "request_size_bytes")} type="number" min="16" max="4096" step="16" value="${row.request_size_bytes}"></td>
      <td><input data-stimulus-field="read_ratio" ${configHelpAttributes("stimulus", "read_ratio")} type="number" min="0" max="1" step="0.05" value="${row.read_ratio}"></td>
      <td><input data-stimulus-field="working_set_mb" ${configHelpAttributes("stimulus", "working_set_mb")} type="number" min="1" max="262144" step="1" value="${row.working_set_mb}"></td>
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
      rate_value: Number(value("rate_value").value),
      rate_unit: value("rate_unit").value,
      request_size_bytes: Number(value("request_size_bytes").value),
      read_ratio: Number(value("read_ratio").value),
      working_set_mb: Number(value("working_set_mb").value),
      target_p99_ns: Number(value("target_p99_ns").value),
    };
  });
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

async function loadDefaults() {
  const payload = await requestJson("/api/defaults");
  state.uiMetadata = payload.ui_metadata || {};
  algorithmHelp = {
    ...supplementalAlgorithmHelp,
    ...(state.uiMetadata.control_algorithms || {}),
  };
  state.defaults = payload.parameters;
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
      <span><i></i>P${partid}</span>
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
        ? `${formatTime(Number(latest.time_ns || 0))} · P${escapeHtml(latest.partid)} · ${escapeHtml(latest.target_msc)}.${escapeHtml(latest.field)} · ${escapeHtml(latest.reason)}`
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
      "OSTD Util %", "Core Pool / P OSTD", "Home MC P OSTD",
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
        <td><strong>${formatNumber(row.coreOutstanding, 0)}</strong> / ${formatNumber(row.corePeakOutstanding, 0)} <small>limit ${formatNumber(row.coreLimit, 0)} · P ${formatNumber(row.corePartidOutstanding, 0)} / ${formatNumber(row.corePartidPeakOutstanding, 0)} · ${escapeHtml([...row.corePolicies].join(" / ") || "-")}</small></td>
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
      "PARTID", "Control State", "Physical / Raw / Filtered",
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
  renderResourceMonitor();
  renderControlEffect();
  renderEvidenceTimeline();
  renderExperiment();
  renderControlVerification();
  renderCausalTimeline();
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
  const algorithmText = `MC ${formatNumber(algorithm.mc_clock_mhz, 0)} MHz · ${formatNumber(algorithm.mc_monitor_period_cycles, 0)}拍 · filter ${formatNumber(algorithm.mc_history_weight, 0)}/${formatNumber(algorithm.mc_current_weight, 0)} · ${escapeHtml(algorithm.mc_aging_mode || "none")} +${formatNumber(algorithm.mc_qos_aging_max_steps, 0)}档 · BMIN +${formatNumber(algorithm.mc_bmin_qos_promote, 0)} · soft -${formatNumber(algorithm.mc_softlimit_qos_demote, 0)}`;
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
    Number(parameters.mc_history_weight)
    + Number(parameters.mc_current_weight)
    !== 256
  ) {
    add("error", "MC History Weight 与 Current Weight 之和必须等于 256。");
  }
  if (
    Number(parameters.l3_history_weight)
    + Number(parameters.l3_current_weight)
    !== 256
  ) {
    add("error", "L3 History Weight 与 Current Weight 之和必须等于 256。");
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
  if (!messages.length) {
    add("ok", `配置检查通过：${stimuli.length} 个激励，${activePartids.size} 个活动 PARTID。`);
  }
  return messages;
}

function renderConfigDiagnostics() {
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

function drawLineChart(canvas, series, options = {}) {
  const { ctx, width, height } = prepareCanvas(canvas);
  const pad = { left: 48, right: 15, top: 12, bottom: 28 };
  ctx.clearRect(0, 0, width, height);
  const points = series.flatMap((entry) => entry.points);
  if (!points.length) {
    ctx.fillStyle = "#7b8790";
    ctx.font = "12px sans-serif";
    ctx.fillText("等待仿真数据", 16, 34);
    return;
  }
  const maxX = Math.max(1, ...points.map((point) => point.x));
  const maxY = Number(options.yMax)
    || Math.max(1, ...points.map((point) => point.y)) * 1.08;
  const x = (value) => pad.left + (value / maxX) * (width - pad.left - pad.right);
  const y = (value) => height - pad.bottom - (value / maxY) * (height - pad.top - pad.bottom);

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
  ctx.fillText(formatTime(maxX), Math.max(pad.left, width - 78), height - 8);

  series.forEach((entry) => {
    if (!entry.points.length) return;
    ctx.strokeStyle = entry.color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    entry.points.forEach((point, index) => {
      if (index === 0) ctx.moveTo(x(point.x), y(point.y));
      else ctx.lineTo(x(point.x), y(point.y));
    });
    ctx.stroke();
    const last = entry.points[entry.points.length - 1];
    ctx.fillStyle = entry.color;
    ctx.beginPath();
    ctx.arc(x(last.x), y(last.y), 3.5, 0, Math.PI * 2);
    ctx.fill();
  });
}

function drawBarChart(canvas, bars) {
  const { ctx, width, height } = prepareCanvas(canvas);
  ctx.clearRect(0, 0, width, height);
  if (!bars.length) {
    ctx.fillStyle = "#7b8790";
    ctx.font = "12px sans-serif";
    ctx.fillText("等待仿真数据", 16, 34);
    return;
  }
  const pad = { left: 42, right: 12, top: 12, bottom: 45 };
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
  ctx.textAlign = "left";
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

function renderCharts() {
  const latencySeries = metricSeries("p99_latency_ns");
  $("#latencyLegend").innerHTML = latencySeries.map((entry) =>
    `<span><i style="background:${entry.color}"></i>P${entry.partid}</span>`
  ).join("");
  drawLineChart($("#latencyChart"), latencySeries);
  drawLineChart($("#bandwidthChart"), metricSeries("throughput_gbps"));

  const queueRows = visibleRows(state.partial.msc);
  const groups = new Map();
  queueRows.forEach((row) => {
    const id = String(row.msc_id);
    if (!groups.has(id)) groups.set(id, { color: id === "noc" ? colors.green : colors.amber, points: [] });
    groups.get(id).points.push({ x: Number(row.time_ns), y: Number(row.queue_occupancy || 0) });
  });
  drawLineChart($("#queueChart"), [...groups.values()]);

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
  drawBarChart($("#delayChart"), bars);
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
  const times = new Set();
  (state.partial.metrics || []).forEach((row) => {
    if (Number(row.partid) === pid) times.add(Number(row.time_ns));
  });
  (state.partial.msc || []).forEach((row) => times.add(Number(row.time_ns)));
  const controls = state.partial.controls || [];
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
      const occupancy = cacheValues.reduce(
        (sum, row) => sum + Number(row.estimated_occupancy_bytes || 0),
        0,
      );
      const cacheCapacity = cacheValues.reduce(
        (sum, row) => sum + Number(row.cache_capacity_bytes || 0),
        0,
      );
      const mcRequests = mcValues.reduce(
        (sum, row) => sum + Number(row.requests || 0),
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
        l3Share: occupancy * 100 / Math.max(1, cacheCapacity),
        l3Contended: cacheValues.some(
          (row) => Number(row.allocation_denials || 0) > 0
            || Number(row.cmin_protected_evictions || 0) > 0,
        ),
        mcBandwidth: mcValues.reduce(
          (sum, row) => sum + Number(row.achieved_bandwidth_gbps || 0),
          0,
        ),
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
    ? "未达标"
    : row.l3Contended ? "达标" : "观察";
  const bw = bwMaxFail || bwMinFail
    ? "未达标"
    : row.mcContended || target.mode === "hardlimit" ? "达标" : "借用";
  return {
    l3,
    bw,
    overall: l3 === "未达标" || bw === "未达标" ? "需检查" : "符合模型",
  };
}

function stateBadge(value) {
  const kind = value === "未达标" || value === "需检查"
    ? "fail"
    : value === "达标" || value === "符合模型"
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
  drawLineChart($("#effectL3Chart"), [
    { color: partidColor(state.effectPartid), points: points("l3Share") },
    { color: "#2d7a4c", points: targetSeries(target.cmin) },
    { color: "#b43a3a", points: targetSeries(target.cmax) },
  ], { yMax: 100 });
  drawLineChart($("#effectBwChart"), [
    { color: partidColor(state.effectPartid), points: points("mcBandwidth") },
    { color: "#2d7a4c", points: targetSeries(target.bmin) },
    { color: "#b43a3a", points: targetSeries(target.bmax) },
  ]);
  drawLineChart($("#effectQosChart"), [
    { color: "#697680", points: points("baseQos") },
    { color: partidColor(state.effectPartid), points: points("effectiveQos") },
  ], { yMax: 8 });
  drawLineChart($("#effectP99Chart"), [
    { color: partidColor(state.effectPartid), points: points("p99") },
    { color: "#b43a3a", points: targetSeries(target.p99) },
  ]);

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
        <td>${latest ? `${formatNumber(latest.l3Share, 2)}%` : "-"}</td>
        <td>${stateBadge(rowState.l3)}</td>
        <td>${rowTarget.bmin == null ? "-" : formatNumber(rowTarget.bmin, 1)} / ${rowTarget.bmax == null ? "-" : formatNumber(rowTarget.bmax, 1)} <small>${escapeHtml(rowTarget.mode)}</small></td>
        <td>${latest ? `${formatNumber(latest.mcBandwidth, 3)} Gbps` : "-"}</td>
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
        <td>${formatNumber(row.l3Share, 2)}%</td>
        <td>${target.cmin == null ? "-" : `${formatNumber(target.cmin, 1)}%`} / ${target.cmax == null ? "-" : `${formatNumber(target.cmax, 1)}%`} <small>${row.l3Contended ? "replacement pressure" : "no replacement pressure"}</small></td>
        <td>${formatNumber(row.mcBandwidth, 3)} Gbps</td>
        <td>${target.bmin == null ? "-" : formatNumber(target.bmin, 1)} / ${target.bmax == null ? "-" : formatNumber(target.bmax, 1)} <small>${row.mcContended ? "contended" : target.mode}</small></td>
        <td>${formatNumber(row.baseQos, 0)} / ${formatNumber(row.effectiveQos, 2)}</td>
        <td>L${row.cbusy} / ${formatNumber(row.outstanding, 0)} of ${formatNumber(row.ostdCap, 0)}</td>
        <td>${formatNumber(row.p99, 2)} ns / ${formatNumber(row.throughput, 3)} Gbps</td>
        <td class="causal-events">${row.events.length ? row.events.map((event) =>
          `<span><b>${escapeHtml(event.target_msc)}</b> ${escapeHtml(event.field)} ${escapeHtml(event.old_value)}→${escapeHtml(event.new_value)}</span>`
        ).join("") : '<span class="muted">无更新</span>'}</td>
      </tr>`).join("")
    : '<tr><td colspan="9" class="empty-cell">选择 PARTID 后显示完整时间线</td></tr>';
}

function renderEvidenceTimeline() {
  const canvas = document.getElementById('evEventCanvas');
  if (!canvas) return;
  const events = collector.control_rows;
  if (!events || events.length === 0) {
    canvas.style.display = 'none';
    return;
  }
  canvas.style.display = 'block';
  canvas.width = canvas.parentElement.clientWidth;
  canvas.height = 100;
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  const maxTime = state.totalTimeNs || 1;
  const colors = { setting_applied: '#2563eb', cbusy_update: '#ea580c', feedback_delivered: '#7c3aed' };
  const yPos = { setting_applied: 20, cbusy_update: 50, feedback_delivered: 78 };
  const partidColors = ['#2563eb','#ea580c','#16a34a','#d97706','#7c3aed','#db2777','#0891b2','#4f46e5',
    '#65a30d','#c026d3','#0284c7','#b45309','#059669','#be185d','#1d4ed8','#854d0e'];

  ctx.fillStyle = '#94a3b8';
  ctx.font = '9px system-ui';
  ctx.fillText('控制事件', 4, 10);

  for (const evt of events) {
    const x = (evt.time_ns / maxTime) * w;
    if (x < 0 || x > w) continue;
    const color = partidColors[evt.partid % 16] || '#64748b';
    const y = yPos[evt.event_type] || 35;
    ctx.fillStyle = color;
    ctx.fillRect(x - 1, y - 1, 3, 3);
  }
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
    return `<p>${escapeHtml(entry.body)}</p>`;
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
  return Object.entries(labels).map(([key, label]) => `
    <section class="algorithm-detail">
      <h4>${escapeHtml(label)}</h4>
      <p>${escapeHtml(entry[key] || "未定义")}</p>
    </section>
  `).join("");
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

function bindEvents() {
  bindHelpEvents();
  bindAlgorithmEvents();
  $$(".tab-button").forEach((button) => button.addEventListener("click", () => {
    $$(".tab-button").forEach((node) => node.classList.toggle("active", node === button));
    $$(".config-section").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab));
    $("#configForm").scrollLeft = 0;
    $(".workspace").classList.toggle(
      "config-wide",
      button.dataset.tab === "mpam" || button.dataset.tab === "traffic",
    );
  }));
  $$(".result-tab").forEach((button) => button.addEventListener("click", () => {
    $$(".result-tab").forEach((node) => node.classList.toggle("active", node === button));
    $$(".result-view").forEach((view) => view.classList.toggle("active", view.dataset.resultView === button.dataset.resultTab));
    if (button.dataset.resultTab === "control-effect") {
      renderControlEffect();
      requestAnimationFrame(renderControlEffect);
    }
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
      === "control-effect"
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
