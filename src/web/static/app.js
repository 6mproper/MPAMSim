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
  populatePartidSelects();
  renderPartidConfig(
    values.partid_configs || state.defaults.partid_configs || [],
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
  return parameters;
}

function populatePartidSelects() {
  $$(".partid-select").forEach((select) => {
    if (select.options.length === 16) return;
    select.innerHTML = Array.from({ length: 16 }, (_, partid) =>
      `<option value="${partid}">PARTID ${partid}</option>`
    ).join("");
  });
}

function partidColor(partid) {
  return partidPalette[Number(partid) % partidPalette.length];
}

function renderPartidConfig(rows) {
  state.partidConfigs = rows.map((row) => ({ ...row }));
  $("#partidConfigTable").innerHTML = state.partidConfigs.map((row) => `
    <tr data-partid-row="${row.partid}">
      <td><span class="partid-chip" style="background:${partidColor(row.partid)}">${row.partid}</span></td>
      <td><input data-field="name" type="text" value="${escapeHtml(row.name)}" spellcheck="false"></td>
      <td><input data-field="monitor_enable" type="checkbox" ${row.monitor_enable ? "checked" : ""}></td>
      <td><input data-field="cmin" type="number" min="0" max="32" step="1" value="${row.cmin}"></td>
      <td><input data-field="cmax" type="number" min="0" max="32" step="1" value="${row.cmax}"></td>
      <td><input data-field="cpbm" type="text" value="${escapeHtml(row.cpbm)}" spellcheck="false"></td>
      <td><input data-field="bmin_gbps" type="number" min="0" max="4096" step="1" value="${row.bmin_gbps}"></td>
      <td><input data-field="bmax_gbps" type="number" min="0" max="4096" step="1" value="${row.bmax_gbps}"></td>
      <td><select data-field="limit_mode">
        <option value="softlimit" ${row.limit_mode === "softlimit" ? "selected" : ""}>soft</option>
        <option value="hardlimit" ${row.limit_mode === "hardlimit" ? "selected" : ""}>hard</option>
      </select></td>
      <td><input data-field="priority" type="number" min="0" max="15" step="1" value="${row.priority}"></td>
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
  const cores = Number($('[data-param="active_cores"]').value || 2);
  const bg = $('[data-param="background_cores"]');
  bg.max = Math.max(1, cores - 1);
  if (Number(bg.value) > Number(bg.max)) bg.value = bg.max;
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
  renderMpamMonitorTable();
  renderMscTable();
  renderControlTable();
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
  const protectedPartid = String($('[data-param="protected_partid"]').value);
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
  $$(".tab-button").forEach((button) => button.addEventListener("click", () => {
    $$(".tab-button").forEach((node) => node.classList.toggle("active", node === button));
    $$(".config-section").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab));
    $(".workspace").classList.toggle("mpam-wide", button.dataset.tab === "mpam");
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
  });
  $("#playButton").addEventListener("click", togglePlayback);
  $("#timeSlider").addEventListener("input", (event) => {
    stopPlayback();
    state.selectedTime = Number(event.target.value);
    $("#timeOutput").textContent = formatTime(state.selectedTime);
    renderAll();
  });
  $('[data-param="active_cores"]').addEventListener("input", clampDependentInputs);
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
    setStatus("ready", "调整参数后运行仿真", 0);
    renderAll();
  } catch (error) {
    failRun(error.message);
  }
}

init();
