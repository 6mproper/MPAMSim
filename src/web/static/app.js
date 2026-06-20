const state = {
  defaults: {},
  jobId: null,
  experimentJobId: null,
  polling: null,
  experimentPolling: null,
  result: null,
  experiment: null,
  experimentPartial: null,
  partial: { metrics: [], cpu: [], msc: [], controls: [], time_ns: 0 },
  selectedTime: 0,
  playing: false,
  playTimer: null,
  partidConfigs: [],
  stimulusConfigs: [],
  resourceView: "cpu",
  causalPartid: 0,
  experimentPartid: 0,
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
  cbusy_sample_ns: "MC 对每个 PARTID 评估 CBusy 的快速采样周期，独立于慢速软件控制周期。",
  cbusy_feedback_latency_ns: "MC CBusy 档位变化传播到 CPU requester 的模型延迟。",
  cbusy_release_hold_samples: "压力下降后连续满足该采样数才允许 CBusy 逐级释放。",
  cbusy_l1_bw_ratio: "Level 1 带宽阈值：采样带宽除以启用的 BMAX。",
  cbusy_l2_bw_ratio: "Level 2 带宽阈值，必须不小于 Level 1。",
  cbusy_l3_bw_ratio: "Level 3 带宽阈值，必须不小于 Level 2。",
  cbusy_l1_queue_ratio: "Level 1 队列阈值：该 PARTID 队列深度除以 MC 总队列容量。",
  cbusy_l2_queue_ratio: "Level 2 队列阈值，必须不小于 Level 1。",
  cbusy_l3_queue_ratio: "Level 3 队列阈值，必须不小于 Level 2。",
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
  cpbm_enable: "独立启用 CPBM；关闭时所有物理 way 都可参与分配。",
  cmin_enable: "独立启用 CMIN 替换保护；关闭后最低 way 保护为 0。",
  cmax_enable: "独立启用 CMAX；关闭后有效上限由 CPBM 可用 way 数决定。",
  cmin: "Cache minimum：抽样替换时保护该 PARTID 的最低 way 占有目标。",
  cmax: "Cache maximum：该 PARTID 在每个抽样 set 内最多可分配的 way 数。",
  cpbm: "Cache Portion Bitmap：十六进制 way 允许位图，bit N 对应 way N。",
  bmin_gbps: "每个 MC 上该 PARTID 的最小带宽目标；低于目标时获得调度加权。",
  bmax_gbps: "每个 MC 上该 PARTID 的最大带宽目标。",
  bmin_enable: "独立启用 BMIN 调度加权。",
  bmax_enable: "独立启用 BMAX hard token 或 soft contention penalty。",
  limit_mode: "soft：无竞争时可借用带宽，竞争且超限时降优先级；hard：token 不足时停止调度。",
  priority: "PARTID 的基础调度优先级，影响 NoC 和 MC 发生竞争时的选择顺序。",
  priority_enable: "独立启用 priority；关闭后保留配置值但有效贡献为 0。",
  cbusy_enable: "启用该 PARTID 的 MC 四档 CBusy 源端反馈。",
  cbusy_ostd: "CBusy Level 1/2/3 对应的 requester effective OSTD 上限。",
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
  "CBusy / OSTD": `${partidFieldHelp.cbusy_enable}\n${partidFieldHelp.cbusy_ostd}`,
  "PARTID / PMG": "软件可见监控 key。PARTID 选择控制策略，PMG 细分同一控制分区内的监控归因。",
  "L3 Sample BW": "该监控组在 L3 抽样 set 上观察到并按 8 倍估算的访问带宽。",
  "L3 Est. Occupancy": "该监控组在抽样 way 中的所有权按 8-set 分组放大的估算字节数。",
  "L3 Occupancy %": "估算占用字节除以该 PARTID 当前允许的 L3 容量；这是近似 CSU，不是精确 tag-array 统计。",
  "MC BW": "该监控组在所有内存控制器上实际完成服务的带宽之和。",
  "MC BW Util %": "监控组 MC 带宽除以参与统计的 MC 总建模带宽。",
  "MC Requests": "最新采样周期内该监控组在 MC 完成调度的请求数。",
  "Throttle ns": "最新周期内 hard limit 等待累计时间。",
  "OSTD Current / Peak": "采样时刻当前 outstanding requests，以及该控制周期内观察到的峰值。",
  "OSTD Util %": "当前 outstanding 除以该 PARTID 所关联 requester 的最大 outstanding 容量之和。",
  "Issued / Completed": "仿真开始以来该 PARTID 在 CPU requester 侧累计发出和完成的请求数。",
  "Backpressure ns": "requester 因 outstanding 达到上限而延迟发出的累计时间。",
  "CBusy": "所有 MC 对该 PARTID 反馈的最高 CBusy 档位及对应 effective OSTD。",
  "CBusy Stall ns": "因 CBusy-derived effective OSTD 达到上限而产生的源端累计等待。",
  "L3 Occupancy": "所有 L3 实例的 8-set 抽样占用估算之和。",
  "L3 Util %": "估算 L3 占用除以该 PARTID 在所有 L3 实例上的允许容量。",
  "Hit Rate": "最新采样周期内该 PARTID 在 L3 的概率命中率。",
  "Alloc Denials": "因 CPBM 或 CMAX 无可用 way 而拒绝抽样分配的次数。",
  "MC Util %": "该 PARTID 在所有 MC 上的带宽之和除以这些 MC 的总建模带宽。",
  "Avg Queue ns": "最新采样周期内该 PARTID 在 MC 队列中的平均等待时间。",
  "Limit Events": "softlimit 低偏好请求数与 hardlimit 阻塞检查事件数。",
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
  "Soft Req": "超出 soft BMAX 且发生竞争时被标记为低偏好的请求数。",
  "Hard Blocks": "因 hard BMAX token 不足而无法调度的检查事件数。",
};
const resultTabHelp = {
  "资源监控": "在 CPU、L3、MC 之间切换，并用同一组 PARTID 开关查看资源状态和控制反馈。",
  "对照实验": "使用相同输入自动比较参考、BMAX-only、CBusy-only和组合控制的收益与代价。",
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
  "16 线程独立激励": workloadTypeComparison,
  "16 PARTID Cache / Memory 控制": "每行配置一个 PARTID 的 L3 分配、MC 带宽、优先级和监控开关。",
  "控制模式": "选择是否执行 MPAM 控制，以及是否允许运行时闭环更新。",
  "闭环参数": "控制闭环的步长、滞回和最小保持时间，避免频繁震荡。",
  "CBusy 快反馈": "配置 MC per-PARTID 四档拥塞检测、反馈传播和逐级恢复行为。",
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
      <td>${controlField("cmin_enable", row.cmin_enable, "cmin", row.cmin, partidFieldHelp.cmin_enable, partidFieldHelp.cmin, 'type="number" min="0" max="32" step="1"')}</td>
      <td>${controlField("cmax_enable", row.cmax_enable, "cmax", row.cmax, partidFieldHelp.cmax_enable, partidFieldHelp.cmax, 'type="number" min="0" max="32" step="1"')}</td>
      <td>${controlField("cpbm_enable", row.cpbm_enable, "cpbm", row.cpbm, partidFieldHelp.cpbm_enable, partidFieldHelp.cpbm, 'type="text" spellcheck="false"')}</td>
      <td>${controlField("bmin_enable", row.bmin_enable, "bmin_gbps", row.bmin_gbps, partidFieldHelp.bmin_enable, partidFieldHelp.bmin_gbps, 'type="number" min="0" max="4096" step="1"')}</td>
      <td>${controlField("bmax_enable", row.bmax_enable, "bmax_gbps", row.bmax_gbps, partidFieldHelp.bmax_enable, partidFieldHelp.bmax_gbps, 'type="number" min="0" max="4096" step="1"')}</td>
      <td><select data-field="limit_mode" data-help="${escapeHtml(partidFieldHelp.limit_mode)}">
        <option value="softlimit" title="无竞争时可借用空闲带宽，竞争且超限时降低调度优先级。" ${row.limit_mode === "softlimit" ? "selected" : ""}>soft</option>
        <option value="hardlimit" title="超过 BMAX 且 token 不足时阻塞请求，直到预算恢复。" ${row.limit_mode === "hardlimit" ? "selected" : ""}>hard</option>
      </select></td>
      <td>${controlField("priority_enable", row.priority_enable, "priority", row.priority, partidFieldHelp.priority_enable, partidFieldHelp.priority, 'type="number" min="0" max="15" step="1"')}</td>
      <td>
        <div class="cbusy-control">
          <input data-field="cbusy_enable" data-help="${escapeHtml(partidFieldHelp.cbusy_enable)}" type="checkbox" ${row.cbusy_enable ? "checked" : ""}>
          <div data-help="${escapeHtml(partidFieldHelp.cbusy_ostd)}">
            <input data-field="cbusy_l1_ostd" type="number" min="1" max="1024" step="1" value="${row.cbusy_l1_ostd}">
            <input data-field="cbusy_l2_ostd" type="number" min="1" max="1024" step="1" value="${row.cbusy_l2_ostd}">
            <input data-field="cbusy_l3_ostd" type="number" min="1" max="1024" step="1" value="${row.cbusy_l3_ostd}">
          </div>
        </div>
      </td>
    </tr>
  `).join("");
}

function controlField(enableField, enabled, valueField, value, enableHelp, valueHelp, attributes) {
  return `
    <div class="control-field">
      <input data-field="${enableField}" data-help="${escapeHtml(enableHelp)}" type="checkbox" ${enabled ? "checked" : ""}>
      <input data-field="${valueField}" data-help="${escapeHtml(valueHelp)}" ${attributes} value="${escapeHtml(value)}">
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
      priority_enable: value("priority_enable").checked,
      priority: Number(value("priority").value),
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
  state.defaults = payload.parameters;
  fillForm(state.defaults);
}

async function runSimulation() {
  stopPlayback();
  clearTimeout(state.polling);
  state.partidConfigs = collectPartidConfigs();
  state.stimulusConfigs = collectStimulusConfigs();
  state.result = null;
  state.partial = { metrics: [], cpu: [], msc: [], controls: [], time_ns: 0 };
  state.selectedTime = 0;
  $("#runButton").disabled = true;
  $("#experimentButton").disabled = true;
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
  setStatus("failed", "对照实验失败", 0);
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
        msc: job.result.msc,
        controls: job.result.controls,
        time_ns: job.result.summary.simulation_time_ns,
      };
      state.selectedTime = state.partial.time_ns;
      $("#runButton").disabled = false;
      $("#experimentButton").disabled = false;
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
  }));
  const configured = collectStimulusConfigs().filter((row) => row.enabled);
  configured.forEach((row) => result[row.partid].requesters.add(row.requester));
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
  });
  const configuredMax = Number($('[data-param="max_outstanding"]')?.value || 0);
  result.forEach((row) => {
    if (row.maxOutstanding === 0 && row.requesters.size) {
      row.maxOutstanding = row.requesters.size * configuredMax;
    }
    if (row.effectiveMaxOutstanding === 0 && row.requesters.size) {
      row.effectiveMaxOutstanding = row.maxOutstanding;
    }
    row.outstandingUtilization = Math.min(
      1,
      row.outstanding / Math.max(1, row.effectiveMaxOutstanding),
    );
    row.completionRatio = row.completed / Math.max(1, row.issued);
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
    capacity: 0,
    requests: 0,
    hits: 0,
    misses: 0,
    allocationDenials: 0,
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
      Object.entries(row.per_partid || {}).forEach(([pidText, values]) => {
        const partid = Number(pidText);
        if (!Number.isInteger(partid) || partid < 0 || partid > 15) return;
        const target = result[partid];
        target.bandwidth += Number(values.estimated_bandwidth_gbps || 0);
        target.occupancy += Number(values.estimated_occupancy_bytes || 0);
        target.capacity += Number(values.allowed_capacity_bytes || 0);
        target.requests += Number(values.requests || 0);
        target.hits += Number(values.hits || 0);
        target.misses += Number(values.misses || 0);
        target.allocationDenials += Number(values.allocation_denials || 0);
        target.cminByMsc.set(String(row.msc_id), values.cmin);
        target.cmaxByMsc.set(String(row.msc_id), values.cmax);
        target.cpbmByMsc.set(String(row.msc_id), values.cpbm);
        target.configuredCminByMsc.set(
          String(row.msc_id),
          values.configured_cmin,
        );
        target.configuredCmaxByMsc.set(
          String(row.msc_id),
          values.configured_cmax,
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
    if (update.field === "cache_min_ways") {
      target.cminByMsc.set(mscId, update.new_value);
    } else if (update.field === "cache_max_ways") {
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
    row.occupancyUtilization = Math.min(
      1,
      row.occupancy / Math.max(1, row.capacity),
    );
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
    priorityByMsc: new Map(),
    configuredBminByMsc: new Map(),
    configuredBmaxByMsc: new Map(),
    configuredPriorityByMsc: new Map(),
    bminEnabled: false,
    bmaxEnabled: false,
    priorityEnabled: false,
    softRequests: 0,
    hardBlocks: 0,
    cbusyEnabled: false,
    cbusyLevel: 0,
    cbusyBandwidthRatio: 0,
    cbusyQueueRatio: 0,
    cbusyDuty: 0,
    cbusyTransitions: 0,
    cbusyCap: 0,
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
        target.priorityByMsc.set(String(row.msc_id), values.priority);
        target.configuredBminByMsc.set(
          String(row.msc_id),
          values.configured_bmin_gbps,
        );
        target.configuredBmaxByMsc.set(
          String(row.msc_id),
          values.configured_bmax_gbps,
        );
        target.configuredPriorityByMsc.set(
          String(row.msc_id),
          values.configured_priority,
        );
        target.bminEnabled ||= Boolean(values.bmin_enable);
        target.bmaxEnabled ||= Boolean(values.bmax_enable);
        target.priorityEnabled ||= Boolean(values.priority_enable);
        target.softRequests += Number(values.softlimit_requests || 0);
        target.hardBlocks += Number(values.hardlimit_block_events || 0);
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
    } else if (update.field === "priority") {
      target.priorityByMsc.set(mscId, update.new_value);
    }
  });
  result.forEach((row) => {
    const configured = state.partidConfigs[row.partid] || {};
    if (!row.configuredBminByMsc.size) {
      row.bminEnabled = Boolean(configured.bmin_enable);
      row.bmaxEnabled = Boolean(configured.bmax_enable);
      row.priorityEnabled = Boolean(configured.priority_enable);
    }
    if (!row.modeByMsc.size) {
      row.modeByMsc.set("configured", configured.limit_mode);
    }
    if (!row.priorityByMsc.size) {
      row.priorityByMsc.set("configured", configured.priority);
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
    row.priority = singleValue(new Set(row.priorityByMsc.values()));
    row.configuredBmin = [...row.configuredBminByMsc.values()]
      .filter((value) => value != null)
      .reduce((sum, value) => sum + Number(value), 0);
    row.configuredBmax = [...row.configuredBmaxByMsc.values()]
      .filter((value) => value != null)
      .reduce((sum, value) => sum + Number(value), 0);
    row.configuredPriority = singleValue(
      new Set(row.configuredPriorityByMsc.values()),
      configured.priority,
    );
  });
  return result;
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
      "OSTD Util %", "CBusy", "Issued / Completed",
      "Backpressure ns", "CBusy Stall ns",
    ];
    rows = visible(aggregateCpuResources()).map((row) => `
      <tr>
        <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
        <td>${controlStateCell(row.partid)}</td>
        <td>${escapeHtml([...row.requesters].join(", ") || "-")}</td>
        <td><strong>${formatNumber(row.outstanding, 0)}</strong> / ${formatNumber(row.peakOutstanding, 0)} <small>eff ${formatNumber(row.effectiveMaxOutstanding, 0)} · cfg ${formatNumber(row.maxOutstanding, 0)}</small></td>
        <td>${utilizationCell(row.outstandingUtilization, partidColor(row.partid))}</td>
        <td><span class="cbusy-level level-${row.cbusyLevel}">L${row.cbusyLevel}</span> <small>cap ${formatNumber(row.effectiveMaxOutstanding, 0)} · ${formatNumber(row.cbusyTransitions, 0)} trans</small></td>
        <td>${formatNumber(row.issued, 0)} / ${formatNumber(row.completed, 0)} <small>${(row.completionRatio * 100).toFixed(1)}%</small></td>
        <td>${formatNumber(row.backpressureNs, 2)}</td>
        <td>${formatNumber(row.cbusyStallNs, 2)}</td>
      </tr>`);
  } else if (state.resourceView === "l3") {
    headers = [
      "PARTID", "Control State", "L3 Occupancy", "L3 Util %",
      "L3 Sample BW", "Hit Rate", "Alloc Denials", "CMIN", "CMAX", "CPBM",
    ];
    rows = visible(aggregateL3Resources()).map((row) => `
      <tr>
        <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
        <td>${controlStateCell(row.partid)}</td>
        <td>${formatNumber(row.occupancy, 0)} B <small>of ${formatNumber(row.capacity, 0)} B</small></td>
        <td>${utilizationCell(row.occupancyUtilization, "#2d7a4c")}</td>
        <td>${formatNumber(row.bandwidth, 3)} Gbps</td>
        <td>${(row.hitRate * 100).toFixed(2)}%</td>
        <td>${formatNumber(row.allocationDenials, 0)}</td>
        <td>${controlValue(row.cminEnabled, row.cmin, row.configuredCmin, (value) => escapeHtml(value))}</td>
        <td>${controlValue(row.cmaxEnabled, row.cmax, row.configuredCmax, (value) => escapeHtml(value))}</td>
        <td>${controlValue(row.cpbmEnabled, row.cpbm, row.configuredCpbm, (value) => `<code>${escapeHtml(value)}</code>`)}</td>
      </tr>`);
  } else {
    headers = [
      "PARTID", "Control State", "MC BW", "MC Util %", "MC Requests",
      "Avg Queue ns", "Throttle ns", "CBusy Evidence", "BMIN Σ",
      "BMAX Σ", "Mode", "Pri", "Limit Events",
    ];
    rows = visible(aggregateMcResources()).map((row) => `
      <tr>
        <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
        <td>${controlStateCell(row.partid)}</td>
        <td>${formatNumber(row.bandwidth, 3)} Gbps</td>
        <td>${utilizationCell(row.bandwidthUtilization, "#176b9c")}</td>
        <td>${formatNumber(row.requests, 0)}</td>
        <td>${formatNumber(row.avgQueueDelayNs, 2)}</td>
        <td>${formatNumber(row.throttleNs, 2)}</td>
        <td>
          <span class="cbusy-level level-${row.cbusyLevel}">L${row.cbusyLevel}</span>
          <small>${row.cbusyEnabled ? `BW ${row.cbusyBandwidthRatio.toFixed(2)}x · Q ${(row.cbusyQueueRatio * 100).toFixed(1)}% · duty ${(row.cbusyDuty * 100).toFixed(0)}% · ${formatNumber(row.cbusyTransitions, 0)} trans` : "off"}</small>
        </td>
        <td>${controlValue(row.bminEnabled, row.hasBmin ? row.bmin : 0, row.configuredBmin, (value) => formatNumber(value, 1))}</td>
        <td>${controlValue(row.bmaxEnabled, row.hasBmax ? row.bmax : 0, row.configuredBmax, (value) => formatNumber(value, 1))}</td>
        <td>${row.bmaxEnabled ? escapeHtml(row.mode) : '<span class="control-value disabled">off</span>'}</td>
        <td>${controlValue(row.priorityEnabled, row.priority, row.configuredPriority, (value) => escapeHtml(value))}</td>
        <td>${formatNumber(row.softRequests, 0)} soft / ${formatNumber(row.hardBlocks, 0)} hard</td>
      </tr>`);
  }
  $("#resourceMonitorHead").innerHTML = `<tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr>`;
  $(".resource-monitor-table").dataset.resourceView = state.resourceView;
  $("#resourceMonitorTable").innerHTML = rows.length
    ? rows.join("")
    : `<tr><td colspan="${headers.length}" class="empty-cell">未选择 PARTID；使用上方开关选择要显示的分区</td></tr>`;
  $$("#resourceMonitorHead th").forEach((header) => {
    setHelp(header, headerHelp[header.textContent.trim()]);
  });
}

function renderAll() {
  renderKpis();
  renderCharts();
  renderResourceMonitor();
  renderExperiment();
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
  const activePartids = new Set(stimuli.map((row) => row.partid));
  activePartids.forEach((partid) => {
    const row = partids[partid];
    if (row && !row.monitor_enable) {
      add("warning", `PARTID ${partid} 有激励但监控开关关闭。`);
    }
  });

  partids.forEach((row) => {
    if (row.cmin_enable && row.cmax_enable && row.cmin > row.cmax) {
      add("error", `PARTID ${row.partid} 的 CMIN 大于 CMAX。`);
    }
    if (row.cpbm_enable && bitCountHex(row.cpbm) === 0) {
      add("error", `PARTID ${row.partid} 的 CPBM 没有允许任何 way。`);
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
    $("#configForm").scrollLeft = 0;
    $(".workspace").classList.toggle(
      "config-wide",
      button.dataset.tab === "mpam" || button.dataset.tab === "traffic",
    );
  }));
  $$(".result-tab").forEach((button) => button.addEventListener("click", () => {
    $$(".result-tab").forEach((node) => node.classList.toggle("active", node === button));
    $$(".result-view").forEach((view) => view.classList.toggle("active", view.dataset.resultView === button.dataset.resultTab));
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
  $("#experimentPartid").addEventListener("change", (event) => {
    state.experimentPartid = Number(event.target.value);
    renderExperiment();
  });
  $("#causalPartid").addEventListener("change", (event) => {
    state.causalPartid = Number(event.target.value);
    renderCausalTimeline();
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
  $("#configForm").addEventListener("change", renderConfigDiagnostics);
  window.addEventListener("resize", () => requestAnimationFrame(renderCharts));
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
