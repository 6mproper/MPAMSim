const state = {
  defaults: {},
  jobId: null,
  polling: null,
  result: null,
  partial: { metrics: [], msc: [], controls: [], time_ns: 0 },
  selectedTime: 0,
  playing: false,
  playTimer: null,
  partidConfigs: [],
  stimulusConfigs: [],
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

const workloadTypeHelp = {
  stream: "stream：连续递增地址，空间局部性低，容易形成高带宽并污染共享缓存。",
  pointer_chase: "pointer：依赖式随机访问，后一个地址依赖前一个结果，并行度低，主要观察时延。",
  random_read: "random：独立随机读地址，可并发发出，缓存命中率取决于工作集与容量。",
  mixed_rw: "mixed：随机读写混合，Read 决定读比例，用于模拟通用业务和写流量竞争。",
  bursty_dma: "burst：成组突发访问，短时间快速注入后停顿，用于观察队列峰值和背压。",
};
const workloadTypeComparison = Object.values(workloadTypeHelp).join("\n");
const parameterHelp = {
  duration_ns: "仿真结束时间。增大可观察稳态，但会线性增加事件数量。",
  control_interval_ns: "监控采样与闭环控制周期；实时表和图表按此周期刷新。",
  seed: "随机访问、泊松抖动和概率命中的确定性随机种子。",
  active_cores: "交互场景固定 8 核；通用 YAML/Python 接口仍支持其他拓扑。",
  threads_per_core: "交互场景固定每核 2 线程，共 16 个独立 requester。",
  max_outstanding: "每个 requester 最多允许同时未完成的请求数，达到上限时产生源端背压。",
  l3_instances: "共享 L3/SLC 实例数量；核按 cluster 映射到实例。",
  l3_sets: "每个 L3 的 set 数，和 ways、line bytes 共同决定容量。",
  l3_ways: "每个 set 的 way 数，也是 CPBM、CMIN、CMAX 的控制范围。",
  l3_line_size: "缓存行字节数；影响地址映射、占用估算和请求成本。",
  l3_monitor_group_sets: "近似监控固定每 8 个 set 抽样第一个 set，并将观察值按 8 倍估算。",
  l3_hit_latency_ns: "L3 查询固定延迟；命中和未命中都先支付该延迟。",
  noc_routers: "抽象 NoC router 数，影响 requester 附着和平均跳数。",
  noc_link_gbps: "NoC 瓶颈链路的建模带宽。",
  noc_router_latency_ns: "每跳固定 router 延迟。",
  noc_queue_depth: "NoC 瓶颈队列最大 entries，满时 requester 重试并累计背压。",
  noc_virtual_channels: "保留的虚通道数量参数；当前模型主要用于拓扑与容量接口。",
  memory_controllers: "独立内存控制器数量；每个控制器维护自己的 BMIN/BMAX 状态。",
  channels_per_mc: "每个内存控制器的通道数量。",
  channel_bandwidth_gbps: "单通道理论带宽；控制器总带宽为通道数乘以该值。",
  mc_base_latency_ns: "内存控制器服务的固定基础延迟，不含排队和序列化。",
  mc_queue_depth: "每个内存控制器可接收的请求队列深度。",
  max_bw_step_percent: "闭环每次调整背景 PARTID BMAX 的最大百分比。",
  p99_hysteresis: "P99 超过或低于目标的滞回区间，避免控制值频繁抖动。",
  min_hold_intervals: "两次闭环调整之间至少保持的采样周期数。",
};
const stimulusFieldHelp = {
  enabled: "是否为该硬件线程生成 workload。关闭后该 requester 保留但不注入流量。",
  partid: "资源控制标识。L3 和 MC 按 PARTID 查控制表；多个线程可以共享同一 PARTID。",
  pmg: "Performance Monitoring Group，仅用于监控过滤和归因，不作为当前资源控制索引。",
  workload_type: workloadTypeComparison,
  rate_value: "该线程的注入强度；单位由右侧 Unit 选择。",
  rate_unit: "Gbps 按数据位率换算请求间隔；MRPS 表示每秒百万请求数。",
  request_size_bytes: "单个抽象 memory request 的字节数。",
  read_ratio: "读请求比例，0 表示全写，1 表示全读。",
  working_set_mb: "该线程访问的地址工作集大小；相对允许缓存容量越大，命中率通常越低。",
  target_p99_ns: "正值表示该 PARTID 是闭环保护对象；0 表示只监控、不设 P99 目标。",
};
const partidFieldHelp = {
  name: "软件侧分区名称，仅用于识别和导出。",
  monitor_enable: "标记该 PARTID 的监控能力为启用；当前界面仍保留所有 16 行。",
  cmin: "Cache minimum：抽样替换时保护该 PARTID 的最低 way 占有目标。",
  cmax: "Cache maximum：该 PARTID 在每个抽样 set 内最多可分配的 way 数。",
  cpbm: "Cache Portion Bitmap：十六进制 way 允许位图，bit N 对应 way N。",
  bmin_gbps: "每个 MC 上该 PARTID 的最小带宽目标；低于目标时获得调度加权。",
  bmax_gbps: "每个 MC 上该 PARTID 的最大带宽目标。",
  limit_mode: "soft：无竞争时可借用带宽，竞争且超限时降优先级；hard：token 不足时停止调度。",
  priority: "PARTID 的基础调度优先级，影响 NoC 和 MC 发生竞争时的选择顺序。",
};
const headerHelp = {
  "Requester": "固定硬件线程标识，格式为 cpu<核>.t<线程>。",
  "En": stimulusFieldHelp.enabled,
  "PID": stimulusFieldHelp.partid,
  "Name": partidFieldHelp.name,
  "Mon": partidFieldHelp.monitor_enable,
  "PMG": stimulusFieldHelp.pmg,
  "Type": workloadTypeComparison,
  "Rate": stimulusFieldHelp.rate_value,
  "Unit": stimulusFieldHelp.rate_unit,
  "Bytes": stimulusFieldHelp.request_size_bytes,
  "Read": stimulusFieldHelp.read_ratio,
  "WSS MB": stimulusFieldHelp.working_set_mb,
  "P99 ns": stimulusFieldHelp.target_p99_ns,
  "CMIN": partidFieldHelp.cmin,
  "CMAX": partidFieldHelp.cmax,
  "CPBM": partidFieldHelp.cpbm,
  "BMIN": partidFieldHelp.bmin_gbps,
  "BMAX": partidFieldHelp.bmax_gbps,
  "Mode": partidFieldHelp.limit_mode,
  "Pri": partidFieldHelp.priority,
  "PARTID / PMG": "软件可见监控 key。PARTID 选择控制策略，PMG 细分同一控制分区内的监控归因。",
  "L3 Sample BW": "该监控组在 L3 抽样 set 上观察到并按 8 倍估算的访问带宽。",
  "L3 Est. Occupancy": "该监控组在抽样 way 中的所有权按 8-set 分组放大的估算字节数。",
  "L3 Occupancy %": "估算占用字节除以该 PARTID 当前允许的 L3 容量；这是近似 CSU，不是精确 tag-array 统计。",
  "MC BW": "该监控组在所有内存控制器上实际完成服务的带宽之和。",
  "MC BW Util %": "监控组 MC 带宽除以参与统计的 MC 总建模带宽。",
  "MC Requests": "最新采样周期内该监控组在 MC 完成调度的请求数。",
  "Throttle ns": "最新周期内 hard limit 等待累计时间。",
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
  "Soft Req": "超出 soft BMAX 且发生竞争时被标记为低偏好的请求数。",
  "Hard Blocks": "因 hard BMAX token 不足而无法调度的检查事件数。",
};
const resultTabHelp = {
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
  "16 线程独立激励": workloadTypeComparison,
  "16 PARTID Cache / Memory 控制": "每行配置一个 PARTID 的 L3 分配、MC 带宽、优先级和监控开关。",
  "控制模式": "选择是否执行 MPAM 控制，以及是否允许运行时闭环更新。",
  "闭环参数": "控制闭环的步长、滞回和最小保持时间，避免频繁震荡。",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

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
    parameters[input.dataset.param] = value;
  });
  parameters.partid_configs = collectPartidConfigs();
  parameters.stimulus_configs = collectStimulusConfigs();
  return parameters;
}

function selectOptions(values, selected, help = {}) {
  return values.map(([value, label]) =>
    `<option value="${escapeHtml(value)}" title="${escapeHtml(help[value] || "")}" ${String(value) === String(selected) ? "selected" : ""}>${escapeHtml(label)}</option>`
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
      <td><input data-field="name" data-help="${escapeHtml(partidFieldHelp.name)}" type="text" value="${escapeHtml(row.name)}" spellcheck="false"></td>
      <td><input data-field="monitor_enable" data-help="${escapeHtml(partidFieldHelp.monitor_enable)}" type="checkbox" ${row.monitor_enable ? "checked" : ""}></td>
      <td><input data-field="cmin" data-help="${escapeHtml(partidFieldHelp.cmin)}" type="number" min="0" max="32" step="1" value="${row.cmin}"></td>
      <td><input data-field="cmax" data-help="${escapeHtml(partidFieldHelp.cmax)}" type="number" min="0" max="32" step="1" value="${row.cmax}"></td>
      <td><input data-field="cpbm" data-help="${escapeHtml(partidFieldHelp.cpbm)}" type="text" value="${escapeHtml(row.cpbm)}" spellcheck="false"></td>
      <td><input data-field="bmin_gbps" data-help="${escapeHtml(partidFieldHelp.bmin_gbps)}" type="number" min="0" max="4096" step="1" value="${row.bmin_gbps}"></td>
      <td><input data-field="bmax_gbps" data-help="${escapeHtml(partidFieldHelp.bmax_gbps)}" type="number" min="0" max="4096" step="1" value="${row.bmax_gbps}"></td>
      <td><select data-field="limit_mode" data-help="${escapeHtml(partidFieldHelp.limit_mode)}">
        <option value="softlimit" title="无竞争时可借用空闲带宽，竞争且超限时降低调度优先级。" ${row.limit_mode === "softlimit" ? "selected" : ""}>soft</option>
        <option value="hardlimit" title="超过 BMAX 且 token 不足时阻塞请求，直到预算恢复。" ${row.limit_mode === "hardlimit" ? "selected" : ""}>hard</option>
      </select></td>
      <td><input data-field="priority" data-help="${escapeHtml(partidFieldHelp.priority)}" type="number" min="0" max="15" step="1" value="${row.priority}"></td>
    </tr>
  `).join("");
}

function collectPartidConfigs() {
  return $$("[data-partid-row]").map((row) => {
    const value = (field) => row.querySelector(`[data-field="${field}"]`);
    return {
      partid: Number(row.dataset.partidRow),
      name: value("name").value,
      monitor_enable: value("monitor_enable").checked,
      cmin: Number(value("cmin").value),
      cmax: Number(value("cmax").value),
      cpbm: value("cpbm").value,
      bmin_gbps: Number(value("bmin_gbps").value),
      bmax_gbps: Number(value("bmax_gbps").value),
      limit_mode: value("limit_mode").value,
      priority: Number(value("priority").value),
    };
  });
}

function renderStimulusConfig(rows) {
  state.stimulusConfigs = rows.map((row) => ({ ...row }));
  const partidOptions = Array.from(
    { length: 16 },
    (_, partid) => [partid, `P${partid}`],
  );
  const partidOptionHelp = Object.fromEntries(
    Array.from(
      { length: 16 },
      (_, partid) => [partid, `PARTID ${partid}：选择该线程使用的资源控制分区。`],
    ),
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
      <td><input data-stimulus-field="enabled" data-help="${escapeHtml(stimulusFieldHelp.enabled)}" type="checkbox" ${row.enabled ? "checked" : ""}></td>
      <td><select data-stimulus-field="partid" data-help="${escapeHtml(stimulusFieldHelp.partid)}">${selectOptions(partidOptions, row.partid, partidOptionHelp)}</select></td>
      <td><input data-stimulus-field="pmg" data-help="${escapeHtml(stimulusFieldHelp.pmg)}" type="number" min="0" max="15" step="1" value="${row.pmg}"></td>
      <td><select data-stimulus-field="workload_type" data-help="${escapeHtml(workloadTypeComparison)}">${selectOptions(typeOptions, row.workload_type, workloadTypeHelp)}</select></td>
      <td><input data-stimulus-field="rate_value" data-help="${escapeHtml(stimulusFieldHelp.rate_value)}" type="number" min="0" max="4096" step="0.1" value="${row.rate_value}"></td>
      <td><select data-stimulus-field="rate_unit" data-help="${escapeHtml(stimulusFieldHelp.rate_unit)}">${selectOptions([["gbps", "Gbps"], ["mrps", "MRPS"]], row.rate_unit, {gbps: "数据位率，按请求字节数换算请求频率。", mrps: "每秒百万请求数，与单请求字节数无关。"})}</select></td>
      <td><input data-stimulus-field="request_size_bytes" data-help="${escapeHtml(stimulusFieldHelp.request_size_bytes)}" type="number" min="16" max="4096" step="16" value="${row.request_size_bytes}"></td>
      <td><input data-stimulus-field="read_ratio" data-help="${escapeHtml(stimulusFieldHelp.read_ratio)}" type="number" min="0" max="1" step="0.05" value="${row.read_ratio}"></td>
      <td><input data-stimulus-field="working_set_mb" data-help="${escapeHtml(stimulusFieldHelp.working_set_mb)}" type="number" min="1" max="262144" step="1" value="${row.working_set_mb}"></td>
      <td><input data-stimulus-field="target_p99_ns" data-help="${escapeHtml(stimulusFieldHelp.target_p99_ns)}" type="number" min="0" max="1000000" step="1" value="${row.target_p99_ns}"></td>
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
    const enabled = parsed.toString(2).split("1").length - 1;
    const cmax = row.querySelector('[data-field="cmax"]');
    const cmin = row.querySelector('[data-field="cmin"]');
    cmax.max = enabled;
    cmin.max = enabled;
    cmax.value = Math.min(Number(cmax.value), enabled);
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
  state.defaults = payload.parameters;
  fillForm(state.defaults);
}

async function runSimulation() {
  stopPlayback();
  clearTimeout(state.polling);
  state.result = null;
  state.partial = { metrics: [], msc: [], controls: [], time_ns: 0 };
  state.selectedTime = 0;
  $("#runButton").disabled = true;
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
        msc: job.result.msc,
        controls: job.result.controls,
        time_ns: job.result.summary.simulation_time_ns,
      };
      state.selectedTime = state.partial.time_ns;
      $("#runButton").disabled = false;
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
  setStatus("failed", "仿真失败", 0);
  showToast(message);
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

function renderAll() {
  renderKpis();
  renderCharts();
  renderPartidTable();
  renderMonitorGroupTable();
  renderMpamMonitorTable();
  renderMscTable();
  renderControlTable();
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
  const rows = aggregateMonitorGroups();
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
  const maxY = Math.max(1, ...points.map((point) => point.y)) * 1.08;
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
  const rows = visibleRows(state.partial.metrics);
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
    (row) => row.enabled && row.target_p99_ns > 0,
  );
  const protectedPartid = String(targetStimulus?.partid ?? latest[0]?.partid ?? 0);
  const protectedRow = latest.find((row) => String(row.partid) === protectedPartid) || latest[0];
  const bars = protectedRow ? [
    { label: "NoC", value: Number(protectedRow.avg_noc_delay_ns || 0), color: "#4a7a98" },
    { label: "L3", value: Number(protectedRow.avg_cache_delay_ns || 0), color: "#538867" },
    { label: "MC Queue", value: Number(protectedRow.avg_mem_queue_delay_ns || 0), color: "#c17a25" },
    { label: "Service", value: Number(protectedRow.avg_mem_service_delay_ns || 0), color: "#7964a5" },
    { label: "Throttle", value: Number(protectedRow.avg_throttle_delay_ns || 0), color: "#ad4e4e" },
  ] : [];
  drawBarChart($("#delayChart"), bars);
}

function renderPartidTable() {
  const rows = latestBy(state.partial.metrics, "partid");
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
  const rows = visibleRows(state.partial.controls).slice().reverse();
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
  const rows = aggregateMpamMonitors();
  $("#mpamMonitorTable").innerHTML = hasData ? rows.map((row) => `
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
  target.title = text;
  target.setAttribute("aria-describedby", "helpTooltip");
  bindHelpTarget(target);
}

function applyContextHelp() {
  Object.entries(parameterHelp).forEach(([key, text]) => {
    $$(`[data-param="${key}"]`).forEach((input) => {
      setHelp(input.closest("label") || input, text);
    });
  });
  $$("th").forEach((header) => {
    setHelp(header, headerHelp[header.textContent.trim()]);
  });
  $$(".result-tab").forEach((button) => {
    setHelp(button, resultTabHelp[button.textContent.trim()]);
  });
  $$(".config-section h2").forEach((heading) => {
    setHelp(heading, sectionHeadingHelp[heading.textContent.trim()]);
  });
  $$('input[name="policy"]').forEach((input) => {
    const text = {
      no_control: "保留监控，但关闭 NoC 优先级映射和 L3/MC 资源约束。",
      static_mpam: "应用当前表格配置，不在运行期间自动修改控制值。",
      closed_loop_qos: "按控制周期读取 P99；违约时提高保护组优先级并收紧背景组 BMAX。",
    }[input.value];
    setHelp(input.closest("label"), text);
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
    setHelp(stage, flowHelp[stage.querySelector("b")?.textContent.trim()]);
  });
  $$("[data-help]").forEach(bindHelpTarget);
}

function positionHelp(target) {
  const tooltip = $("#helpTooltip");
  const anchor = target.getBoundingClientRect();
  const box = tooltip.getBoundingClientRect();
  let left = Math.min(
    window.innerWidth - box.width - 12,
    Math.max(12, anchor.left),
  );
  let top = anchor.bottom + 8;
  if (top + box.height > window.innerHeight - 12) {
    top = Math.max(12, anchor.top - box.height - 8);
  }
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function showHelp(target) {
  if (!target?.dataset.help) return;
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
  if (!target || target.dataset.helpBound === "true") return;
  if (!target.title) target.title = target.dataset.help || "";
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
  $$(".tab-button").forEach((button) => button.addEventListener("click", () => {
    $$(".tab-button").forEach((node) => node.classList.toggle("active", node === button));
    $$(".config-section").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab));
    $(".workspace").classList.toggle(
      "config-wide",
      button.dataset.tab === "mpam" || button.dataset.tab === "traffic",
    );
  }));
  $$(".result-tab").forEach((button) => button.addEventListener("click", () => {
    $$(".result-tab").forEach((node) => node.classList.toggle("active", node === button));
    $$(".result-view").forEach((view) => view.classList.toggle("active", view.dataset.resultView === button.dataset.resultTab));
  }));
  $("#runButton").addEventListener("click", runSimulation);
  $("#resetButton").addEventListener("click", () => fillForm(state.defaults));
  $("#resetPartidButton").addEventListener("click", () => {
    renderPartidConfig(state.defaults.partid_configs || []);
    normalizePartidMasks();
    applyContextHelp();
  });
  $("#resetStimulusButton").addEventListener("click", () => {
    renderStimulusConfig(state.defaults.stimulus_configs || []);
    applyContextHelp();
  });
  $("#playButton").addEventListener("click", togglePlayback);
  $("#timeSlider").addEventListener("input", (event) => {
    stopPlayback();
    state.selectedTime = Number(event.target.value);
    $("#timeOutput").textContent = formatTime(state.selectedTime);
    renderAll();
  });
  $('[data-param="duration_ns"]').addEventListener("input", clampDependentInputs);
  $('[data-param="l3_ways"]').addEventListener("input", normalizePartidMasks);
  $("#partidConfigTable").addEventListener("change", (event) => {
    if (event.target.matches('[data-field="cpbm"], [data-field="cmin"], [data-field="cmax"]')) {
      normalizePartidMasks();
    }
  });
  window.addEventListener("resize", () => requestAnimationFrame(renderCharts));
}

async function init() {
  bindEvents();
  try {
    await loadDefaults();
    applyContextHelp();
    setStatus("ready", "调整参数后运行仿真", 0);
    renderAll();
  } catch (error) {
    failRun(error.message);
  }
}

init();
