"use strict";

// Mirrors gui/src/network_chart.py: log ms axis, outage bands, 4G strip.
// UI text comes from /api/i18n, the same translations as the desktop panel.
const PING_FLOOR_MS = 5;
const MAX_GAP_SECONDS = 300; // break lines across missing samples (worker or host down)
const REFRESH_MS = 15000;
const LANGUAGE_KEY = "o2-panel-language";
const EVENT_LABEL_KEYS = {
  sms_sent: "event_sms_sent",
  check_completed: "event_check_completed",
  check_failed: "event_check_failed",
  data_usage_reset: "event_usage_reset",
  sms_baseline_reset: "event_baseline_reset",
  sms_inbox_cleared: "event_inbox_cleared",
  modem_restarted: "event_modem_restarted",
  modem_latency_high: "event_latency_high",
  modem_latency_reboot: "event_latency_reboot",
  modem_restart_notification_sent: "event_restart_notification_sent",
  modem_restart_notification_failed: "event_restart_notification_failed",
  manual_action_failed: "event_manual_failed",
  connection_slow_sms: "event_connection_slow_sms",
  modem_auto_restarted: "event_modem_auto_restarted",
  connection_recovered: "event_connection_recovered",
  restart_limit_reached: "event_restart_limit_reached",
  watchdog_failed: "event_watchdog_failed",
};
// Events whose message has no parameters: one runtime_* string each.
const EVENT_MESSAGE_KEYS = {
  data_usage_reset: "runtime_counter_reset",
  sms_baseline_reset: "runtime_baseline_reset",
  modem_restarted: "runtime_modem_restarted",
  modem_latency_reboot: "runtime_latency_reboot",
  modem_restart_notification_sent: "runtime_restart_notification_sent",
  modem_restart_notification_failed: "runtime_restart_notification_failed",
  connection_slow_sms: "runtime_connection_slow_sms",
  modem_auto_restarted: "runtime_modem_auto_restarted",
  connection_recovered: "runtime_connection_recovered",
  restart_limit_reached: "runtime_restart_limit_reached",
};
const ACTION_ERROR_KEYS = {
  wrong_password: "web_wrong_password",
  locked_out: "web_locked_out",
  busy: "web_busy",
  actions_disabled: "web_actions_disabled",
};

let windowSeconds = 21600;
let latest = { status: {}, history: [] };
let latestEvents = [];
let strings = {};
let language = "tr";

const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// Python str.format subset used by the shared strings: {name} and {name:.2f}.
function t(key, values = {}) {
  const template = strings[key] ?? key;
  return template.replace(/\{(\w+)(?::\.(\d+)f)?\}/g, (match, name, digits) => {
    if (!(name in values)) return match;
    const value = values[name];
    return digits === undefined ? String(value) : Number(value).toFixed(Number(digits));
  });
}

const label = (key) => t(key).replace(/:\s*$/, "");

function storedLanguage() {
  try { return localStorage.getItem(LANGUAGE_KEY); } catch { return null; }
}

function rememberLanguage(value) {
  try { localStorage.setItem(LANGUAGE_KEY, value); } catch { /* private mode */ }
}

function preferredLanguage(available) {
  const fromUrl = new URLSearchParams(window.location.search).get("lang");
  const candidates = [fromUrl, storedLanguage(), ...(navigator.languages || [navigator.language])];
  for (const candidate of candidates) {
    const code = String(candidate || "").slice(0, 2).toLowerCase();
    if (code in available) return code;
  }
  return "tr";
}

async function loadLanguage(requested) {
  const bundle = await getJson(`/api/i18n?lang=${encodeURIComponent(requested)}`);
  strings = bundle.strings;
  language = bundle.language;
  document.documentElement.lang = language;
  document.title = t("app_title");
  document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = label(node.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
    node.setAttribute("aria-label", node.placeholder);
  });
  const select = $("language");
  if (!select.options.length) {
    for (const [code, name] of Object.entries(bundle.languages)) select.add(new Option(name, code));
  }
  select.value = language;
  return bundle.languages;
}

function formatTime(value, withDate = true) {
  if (!value) return t("never");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  const options = withDate
    ? { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }
    : { hour: "2-digit", minute: "2-digit", second: "2-digit" };
  return date.toLocaleString(language, options);
}

function formatGb(bytes) {
  return typeof bytes === "number" ? `${(bytes / 1e9).toFixed(2)} GB` : "-";
}

function signalQuality(rsrp, sinr) {
  const hasRsrp = typeof rsrp === "number";
  const hasSinr = typeof sinr === "number";
  if (!hasRsrp && !hasSinr) return null;
  if ((hasRsrp && rsrp < -105) || (hasSinr && sinr < 0)) return "weak";
  if ((hasRsrp && rsrp < -95) || (hasSinr && sinr < 10)) return "fair";
  return "good";
}

function connectionText(status) {
  const state = status.connection_watchdog;
  if (!state || typeof state !== "object") return t("conn_unknown");
  const time = state.next_action_at ? formatTime(state.next_action_at * 1000) : "-";
  if (status.connection_probe_ok === false && state.phase === "healthy") return t("conn_unmeasured");
  switch (state.phase) {
    case "degraded": return t("conn_degraded");
    case "sms_wait": return t("conn_sms_wait", { time });
    case "restart_wait": return t("conn_restart_wait", { count: state.episode_restart_count || 0, time });
    default: return t("conn_healthy");
  }
}

// The worker stores the SMS reason as Turkish text; recognise it like the desktop panel does.
function smsReason(message, triggerCode, thresholdGb) {
  if (triggerCode === "highspeed_exhausted") return t("runtime_trigger_exhausted");
  if (triggerCode === "highspeed_80_percent") return t("runtime_trigger_80");
  const text = String(message || "").toLocaleLowerCase("tr");
  if (text.includes("manuel") || text.includes("manually")) return t("runtime_manual_sms");
  if (text.includes("bağlantı yavaş")) return t("runtime_connection_slow_sms");
  if (/eşi[kğ]/.test(text) || text.includes("threshold")) return t("runtime_threshold", { threshold: thresholdGb || 0 });
  return message;
}

function smsReasonText(status) {
  if (!status.last_sms_reason) return t("no_sms_record");
  return smsReason(status.last_sms_reason, status.last_o2_trigger_code, status.threshold_gb);
}

function eventMessage(event) {
  const type = event.event_type;
  if (type in EVENT_MESSAGE_KEYS) return t(EVENT_MESSAGE_KEYS[type]);
  if (type === "check_completed") return t(event.sms_sent ? "runtime_check_sent" : "runtime_check_no_sms");
  if (type === "sms_inbox_cleared") return t("runtime_inbox_cleared", { count: event.deleted_sms_count || 0 });
  if (type === "modem_latency_high") {
    const values = { count: event.bad_sample_count || 0, limit: event.reboot_after_bad_checks || 0 };
    if (typeof event.latency_ms !== "number") return t("runtime_latency_high_unreachable", values);
    return t("runtime_latency_high", { ...values, latency: event.latency_ms, threshold: event.threshold_ms || 0 });
  }
  if (type === "sms_sent") return smsReason(event.message, event.trigger_code, event.threshold_gb);
  return event.message || "";
}

function renderStatus(status) {
  const today = new Date().toISOString().slice(0, 10);
  $("last-sms").textContent = formatTime(status.last_sms_at);
  $("today-sms").textContent = String(status.statistics_day === today ? status.today_sms_count || 0 : 0);
  $("total-sms").textContent = String(status.total_sms_count || 0);
  $("usage").textContent = formatGb(status.current_usage_bytes);
  $("last-check").textContent = formatTime(status.last_check_at);
  $("connection").textContent = connectionText(status);
  $("reason").textContent = smsReasonText(status);
  $("error").textContent = status.last_error || t("none");
  $("actions-disabled").hidden = Boolean(status.web_actions_enabled);
  $("actions").hidden = !status.web_actions_enabled;
}

function renderSummary(history, status) {
  const last = history[history.length - 1] || {};
  const speeds = history.filter((r) => r.speed_measured);
  const speed = speeds.length ? speeds[speeds.length - 1].download_mbps : null;
  const parts = [];
  if (typeof status.modem_latency_last_ms === "number") {
    parts.push(t("web_modem_summary", { latency: status.modem_latency_last_ms }));
  }
  parts.push(t("chart_summary", {
    ping: typeof last.ping_ms === "number" ? Math.round(last.ping_ms) : "-",
    speed: typeof speed === "number" ? speed.toFixed(1) : "-",
  }));
  const signals = history.filter((r) => signalQuality(r.rsrp, r.sinr));
  if (signals.length) {
    const s = signals[signals.length - 1];
    parts.push(t("chart_signal_summary", {
      rsrp: s.rsrp ?? "-", sinr: s.sinr ?? "-", quality: t(`signal_${signalQuality(s.rsrp, s.sinr)}`),
    }));
  }
  $("summary").textContent = parts.join(" · ");
}

function renderEvents(events) {
  const body = $("events");
  const showRoutine = $("show-routine").checked;
  body.replaceChildren();
  for (const event of events) {
    if (!showRoutine && event.event_type === "check_completed") continue;
    const row = document.createElement("tr");
    const type = EVENT_LABEL_KEYS[event.event_type] ? t(EVENT_LABEL_KEYS[event.event_type]) : event.event_type;
    for (const text of [formatTime(event.timestamp), type, eventMessage(event)]) {
      const cell = document.createElement("td");
      cell.textContent = String(text);
      row.appendChild(cell);
    }
    body.appendChild(row);
  }
}

function chartSeries(history, modemHistory, now) {
  const series = { ping: [], modem: [], speed: [], signal: [] };
  const position = (record) => {
    const t = Date.parse(record.timestamp) / 1000;
    if (Number.isNaN(t) || now - t > windowSeconds || t > now + 60) return null;
    return 1 - (now - t) / windowSeconds;
  };
  for (const record of history) {
    const p = position(record);
    if (p === null) continue;
    series.ping.push([p, typeof record.ping_ms === "number" ? record.ping_ms : null]);
    if ("modem_ms" in record) series.modem.push([p, typeof record.modem_ms === "number" ? record.modem_ms : null]);
    if (record.speed_measured && typeof record.download_mbps === "number") series.speed.push([p, record.download_mbps]);
    const quality = signalQuality(record.rsrp, record.sinr);
    if (quality) series.signal.push([p, quality]);
  }
  const firstModem = series.modem.length ? series.modem[0][0] : 2;
  const older = [];
  for (const record of modemHistory || []) {
    const p = position(record);
    if (p === null || p >= firstModem) continue;
    older.push([p, typeof record.latency_ms === "number" ? record.latency_ms : null]);
  }
  older.sort((a, b) => a[0] - b[0]);
  series.modem = older.concat(series.modem);
  return series;
}

function drawChart() {
  const canvas = $("chart");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight || 240;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const { status, history } = latest;
  const series = chartSeries(history, status.modem_latency_history, Date.now() / 1000);
  const left = 52, right = width - 52, top = 10, bottom = height - 34;
  const x = (p) => left + p * (right - left);
  ctx.font = "11px sans-serif";

  if (!series.ping.length && !series.modem.length && !series.speed.length) {
    ctx.fillStyle = css("--muted");
    ctx.textAlign = "center";
    ctx.fillText(t("chart_no_data"), width / 2, height / 2);
    return;
  }

  const pings = series.ping.concat(series.modem).map((v) => v[1]).filter((v) => v !== null);
  const peak = pings.length ? Math.max(...pings) : 0;
  const pingMax = Math.max(1000, 10 ** Math.ceil(Math.log10(Math.max(peak, 1) * 1.1)));
  const pingY = (v) => {
    const c = Math.min(Math.max(v, PING_FLOOR_MS), pingMax);
    return bottom - (Math.log10(c / PING_FLOOR_MS) / Math.log10(pingMax / PING_FLOOR_MS)) * (bottom - top);
  };
  const speeds = series.speed.map((v) => v[1]);
  const slowMbps = status.connection_slow_threshold_mbps || null;
  const speedTop = Math.max(10, Math.ceil(Math.max(0, slowMbps || 0, ...speeds) * 1.1 / 5) * 5);
  const speedY = (v) => bottom - (Math.min(v, speedTop) / speedTop) * (bottom - top);

  // Internet-unreachable periods behind everything else.
  ctx.fillStyle = css("--outage");
  let start = null;
  for (const [p, v] of series.ping.concat([[1, 0]])) {
    if (v === null && start === null) start = p;
    if (v !== null && start !== null) {
      ctx.fillRect(x(start), top, Math.max(2, x(p) - x(start)), bottom - top);
      start = null;
    }
  }

  ctx.strokeStyle = css("--grid");
  ctx.fillStyle = css("--muted");
  ctx.lineWidth = 1;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let tick = 10; tick <= pingMax; tick *= 10) {
    const y = pingY(tick);
    ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
    ctx.fillText(tick === pingMax ? `${tick} ms` : String(tick), left - 6, y);
  }
  ctx.beginPath(); ctx.moveTo(left, bottom); ctx.lineTo(right, bottom); ctx.stroke();
  ctx.textAlign = "left";
  ctx.fillStyle = css("--speed");
  ctx.fillText(`${speedTop} Mbit/s`, right + 6, top);
  ctx.fillText("0", right + 6, bottom);

  ctx.setLineDash([4, 3]);
  const threshold = status.modem_latency_threshold_ms;
  if (threshold && threshold <= pingMax) {
    ctx.strokeStyle = css("--slow");
    ctx.beginPath(); ctx.moveTo(left, pingY(threshold)); ctx.lineTo(right, pingY(threshold)); ctx.stroke();
  }
  if (slowMbps) {
    ctx.strokeStyle = css("--speed");
    ctx.beginPath(); ctx.moveTo(left, speedY(slowMbps)); ctx.lineTo(right, speedY(slowMbps)); ctx.stroke();
  }
  ctx.setLineDash([]);

  for (const [name, color, lineWidth] of [["modem", "--modem", 1.5], ["ping", "--ping", 2]]) {
    ctx.strokeStyle = css(color);
    ctx.lineWidth = lineWidth;
    let drawing = false;
    let previous = null;
    ctx.beginPath();
    for (const [p, v] of series[name]) {
      if (previous !== null && (p - previous) * windowSeconds > MAX_GAP_SECONDS) drawing = false;
      previous = p;
      if (v === null) {
        drawing = false;
        if (name === "modem") {
          ctx.save(); ctx.strokeStyle = css("--slow"); ctx.lineWidth = 2;
          ctx.stroke(); ctx.beginPath(); ctx.moveTo(x(p), bottom); ctx.lineTo(x(p), bottom - 6); ctx.stroke();
          ctx.restore(); ctx.beginPath();
        }
        continue;
      }
      if (drawing) ctx.lineTo(x(p), pingY(v)); else ctx.moveTo(x(p), pingY(v));
      drawing = true;
    }
    ctx.stroke();
  }

  for (const [p, v] of series.speed) {
    ctx.fillStyle = slowMbps && v < slowMbps ? css("--slow") : css("--speed");
    ctx.beginPath(); ctx.arc(x(p), speedY(v), 3.5, 0, Math.PI * 2); ctx.fill();
  }

  const stripTop = bottom + 5;
  const colors = { good: css("--speed"), fair: css("--fair"), weak: css("--slow") };
  series.signal.forEach(([p, quality], i) => {
    const next = i + 1 < series.signal.length ? series.signal[i + 1][0] : 1;
    const end = Math.min(next, p + 300 / windowSeconds, 1);
    ctx.fillStyle = colors[quality];
    ctx.fillRect(x(p), stripTop, Math.max(1, x(end) - x(p)), 8);
  });
  ctx.fillStyle = css("--muted");
  ctx.textAlign = "right";
  ctx.fillText("4G", left - 6, stripTop + 4);
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "left";
  ctx.fillText(t(`chart_window_${windowSeconds / 3600}h`), left, height - 2);
  ctx.textAlign = "right";
  ctx.fillText(t("chart_now"), right, height - 2);
}

async function getJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

async function refresh() {
  try {
    const [status, history, events] = await Promise.all([
      getJson("/api/status"), getJson("/api/history"), getJson("/api/events"),
    ]);
    latest = { status, history: Array.isArray(history) ? history : [] };
    latestEvents = Array.isArray(events) ? events : [];
    render();
    $("updated").textContent = t("web_updated", { time: formatTime(new Date().toISOString(), false) });
  } catch (error) {
    $("updated").textContent = t("web_connection_error", { error: error.message });
  }
}

function render() {
  renderStatus(latest.status);
  renderSummary(latest.history, latest.status);
  renderEvents(latestEvents);
  drawChart();
}

async function runAction(button) {
  if (!window.confirm(t(button.dataset.confirmKey))) return;
  const title = t(button.dataset.doneKey);
  const result = $("action-result");
  const buttons = document.querySelectorAll("[data-action]");
  buttons.forEach((b) => { b.disabled = true; });
  result.textContent = t("action_running", { title });
  try {
    const response = await fetch(`/api/actions/${button.dataset.action}`, {
      method: "POST",
      headers: { "X-Panel-Password": $("password").value },
    });
    const body = await response.json().catch(() => ({}));
    if (response.ok) result.textContent = t("action_completed", { title });
    else if (ACTION_ERROR_KEYS[body.error]) result.textContent = t(ACTION_ERROR_KEYS[body.error]);
    else result.textContent = t("action_failed", { title, code: response.status });
  } catch (error) {
    result.textContent = t("web_connection_error", { error: error.message });
  } finally {
    buttons.forEach((b) => { b.disabled = false; });
    refresh();
  }
}

document.querySelectorAll("[data-window]").forEach((button) => {
  button.addEventListener("click", () => {
    windowSeconds = Number(button.dataset.window);
    document.querySelectorAll("[data-window]").forEach((b) => b.classList.toggle("active", b === button));
    drawChart();
  });
});
document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runAction(button));
});
$("show-routine").addEventListener("change", () => renderEvents(latestEvents));
$("language").addEventListener("change", async (event) => {
  rememberLanguage(event.target.value);
  await loadLanguage(event.target.value);
  render();
});
window.addEventListener("resize", drawChart);

(async () => {
  try {
    // The first bundle lists the supported languages; switch if the browser prefers another.
    const available = await loadLanguage(storedLanguage() || "tr");
    const preferred = preferredLanguage(available);
    if (preferred !== language) await loadLanguage(preferred);
  } catch (error) {
    $("updated").textContent = `i18n: ${error.message}`;
  }
  await refresh();
  setInterval(refresh, REFRESH_MS);
})();
