const $ = (id) => document.getElementById(id);
const demoMode = new URLSearchParams(location.search).get("demo") === "1";
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const oneDecimal = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const twoDecimals = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const lossPercent = new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 });
let activeRequest;

function setText(id, value) { $(id).textContent = value; }
function utcDate(offsetDays = 0) {
  const date = new Date();
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}
function dateTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "UTC" }).format(new Date(value)) + " UTC";
}
function timeOnly(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "UTC" }).format(new Date(value)) + " UTC";
}
function monthLabel(value) {
  return new Intl.DateTimeFormat("en-GB", { month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}-01T00:00:00Z`));
}
function displayEnergy(value) { return typeof value === "number" ? number.format(value) : "—"; }
function setStatus(label, kind) {
  setText("status-label", label);
  $("status-pill").className = `status-pill is-${kind}`;
}
function showFeedback(message) {
  setText("feedback", message);
  $("feedback").hidden = false;
}
function errorDetail(response, body) {
  return typeof body?.detail === "string" ? body.detail : `HTTP ${response.status}`;
}
async function getJson(url, signal) {
  const response = await fetch(url, { signal });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorDetail(response, body));
  return body;
}

function renderMonthly(points) {
  const chart = $("monthly-chart");
  chart.replaceChildren();
  if (!Array.isArray(points) || !points.length) {
    chart.textContent = "No monthly measurements available.";
    return;
  }
  const peak = Math.max(1, ...points.map((point) => point.p50_mwh));
  const scale = Math.ceil(peak / 300) * 300;
  setText("chart-max", number.format(scale));
  setText("chart-mid-high", number.format(scale * 2 / 3));
  setText("chart-mid-low", number.format(scale / 3));
  chart.style.setProperty("--month-count", points.length);
  for (const point of points) {
    const item = document.createElement("div");
    item.className = "month-column";
    const bar = document.createElement("div");
    bar.className = "month-bar";
    bar.style.height = `${Math.max(0, point.p50_mwh / scale * 150)}px`;
    bar.title = `${monthLabel(point.month)}: ${number.format(point.p50_mwh)} MWh from ${number.format(point.usable_hours)} usable hours`;
    const label = document.createElement("span");
    label.className = "month-label";
    const [month, year] = monthLabel(point.month).split(" ");
    label.innerHTML = `<span>${month}</span><small>${year}</small>`;
    item.append(bar, label);
    chart.append(item);
  }
  chart.setAttribute("aria-label", points.map((point) => `${monthLabel(point.month)}: ${number.format(point.p50_mwh)} MWh observed net energy`).join("; "));
}

function renderEnergy(data, annual) {
  if (!data || typeof data.p50_mwh !== "number") throw new Error("The energy response is incomplete.");
  setText("gross-label", annual ? "Gross AEP" : "Gross energy");
  setText("p50-label", annual ? "Net AEP · P50" : "Net energy · P50");
  setText("p90-label", annual ? "P90" : "P90 energy");
  setText("gross-value", displayEnergy(annual ? data.annualized_gross_mwh : data.gross_energy_mwh));
  setText("p50-value", displayEnergy(annual ? data.annualized_p50_mwh : data.p50_mwh));
  setText("p90-value", displayEnergy(annual ? data.annualized_p90_mwh : data.p90_mwh));
  setText("gross-note", annual ? "Estimated full-year yield before losses" : "Observed period · before losses");
  setText("p50-note", annual ? "Estimated full-year yield after losses" : "Observed period · after losses");
  setText("p90-note", annual ? "Full-year estimate with uncertainty" : "Observed period with uncertainty");
  setText("coverage-value", `${oneDecimal.format(data.usable_coverage_pct)}%`);
  setText("coverage-note", `${number.format(data.usable_hours)} / ${number.format(data.expected_hours)} usable hours`);
  setText("expected-hours", number.format(data.expected_hours));
  setText("observed-hours", number.format(data.observed_hours));
  setText("usable-hours", number.format(data.usable_hours));
  const excluded = data.excluded_readings || {};
  const excludedCount = Object.values(excluded).reduce((sum, value) => sum + (Number(value) || 0), 0);
  setText("excluded-hours", number.format(excludedCount));
  setText("exclusion-note", `Excluded: ${number.format(excluded.missing_speed || 0)} missing, ${number.format(excluded.nonnumeric_speed || 0)} nonnumeric, ${number.format(excluded.invalid_speed || 0)} invalid, ${number.format(excluded.unsupported_unit || 0)} unsupported units, ${number.format(excluded.off_hour || 0)} off-hour.`);
  const partialMonths = annual && data.monthly_energy?.length > 12
    ? " The rolling window touches 13 calendar months, with partial first and last months."
    : "";
  setText("monthly-aside", partialMonths ? "Observed MWh · partial months" : "Observed net energy · MWh");
  setText("method-note", annual
    ? `Annual estimates scale energy from ${number.format(data.usable_hours)} usable hours to ${number.format(data.expected_hours)} expected hours. This assumes missing hours resemble measured hours. Monthly bars show observed net energy and are never scaled.${partialMonths}`
    : "These figures sum only usable hourly measurements in the selected UTC window. Missing hours are not filled in; monthly bars show observed net energy.");
  renderMonthly(data.monthly_energy);
}

function renderMeasurements(rows) {
  const body = $("measurements-body");
  body.replaceChildren();
  if (!rows?.length) {
    const row = body.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 4;
    cell.textContent = "No measurements available yet.";
    return;
  }
  for (const measurement of rows) {
    const row = body.insertRow();
    const values = [dateTime(measurement.timestamp).replace(" UTC", ""), measurement.wind_mast_ms, measurement.wind_hub_ms, measurement.power_mw];
    values.forEach((value, index) => {
      const cell = row.insertCell();
      cell.textContent = index === 0 ? value : (value == null ? "—" : oneDecimal.format(value));
    });
  }
}
function renderRuns(runs, fixtureMode = false) {
  const list = $("run-history");
  list.replaceChildren();
  if (!runs?.length) {
    const item = document.createElement("li");
    item.textContent = "No collection runs recorded yet.";
    list.append(item);
    return;
  }
  for (const run of runs.slice(0, 3)) {
    const item = document.createElement("li");
    item.className = `run-item is-${fixtureMode ? "fixture" : run.status}`;
    const icon = document.createElement("span");
    icon.className = "run-icon";
    icon.textContent = fixtureMode ? "i" : (run.status === "succeeded" ? "✓" : "!");
    const description = document.createElement("span");
    description.textContent = fixtureMode
      ? `Sample data loaded · ${number.format(run.records_seen)} records`
      : (run.status === "succeeded" ? `Collection succeeded · ${number.format(run.records_seen)} records seen` : `Collection ${run.status}${run.error_summary ? ` · ${run.error_summary}` : ""}`);
    const time = document.createElement("time");
    time.textContent = fixtureMode ? dateTime(run.finished_at || run.started_at) : timeOnly(run.finished_at || run.started_at);
    item.append(icon, description, time);
    list.append(item);
  }
}
function renderContext(data) {
  const fixtureMode = data.data_mode === "fixture";
  if (fixtureMode) {
    $("data-badge").hidden = false;
    setText("data-badge", "Local API · Sample data");
  }
  setText("site-name", data.site_name || data.mast_id || "Wind site");
  setText("rated-power", oneDecimal.format(data.rated_power_mw));
  setText("last-measurement", dateTime(data.latest_measurement_at));
  setText("last-sync-caption", fixtureMode ? "Sample loaded:" : "Last successful sync:");
  setText("last-sync", fixtureMode ? dateTime(data.last_success_at) : timeOnly(data.last_success_at));
  setText("next-sync-caption", fixtureMode ? "Scheduler:" : "Next scheduled sync:");
  setText("next-sync", fixtureMode ? "Not running in test mode" : timeOnly(data.next_sync_at));
  setStatus(demoMode ? "Demo preview" : (fixtureMode ? "Local test data" : (data.collection_healthy ? "Operational" : "Needs attention")), demoMode || fixtureMode ? "demo" : (data.collection_healthy ? "healthy" : "warning"));
  const input = data.inputs || {};
  setText("measurement-height", input.measurement_height_m == null ? "—" : `${number.format(input.measurement_height_m)} m`);
  setText("hub-height", input.hub_height_m == null ? "—" : `${number.format(input.hub_height_m)} m`);
  setText("shear", input.shear_exponent == null ? "—" : twoDecimals.format(input.shear_exponent));
  for (const [id, key] of [["availability-loss", "availability_loss"], ["electrical-loss", "electrical_loss"], ["wake-loss", "wake_loss"], ["uncertainty", "uncertainty"]]) {
    setText(id, input[key] == null ? "—" : `${lossPercent.format(input[key] * 100)}%`);
  }
  const healthy = data.collection_healthy;
  $("health-summary").replaceChildren();
  const line = document.createElement("div");
  line.className = `health-line ${fixtureMode ? "is-demo" : (healthy ? "is-good" : "is-bad")}`;
  const icon = document.createElement("span");
  icon.className = "run-icon";
  icon.textContent = fixtureMode ? "i" : (healthy ? "✓" : "!");
  const message = document.createElement("span");
  message.textContent = fixtureMode ? "Test mode · ingestion is not running" : (healthy ? "Latest sync succeeded" : "Collection needs attention");
  const time = document.createElement("time");
  time.textContent = fixtureMode ? "" : timeOnly(data.last_success_at);
  line.append(icon, message, time);
  $("health-summary").append(line);
  renderMeasurements(data.recent_measurements);
  renderRuns(data.recent_runs, fixtureMode);
}

function demoData() {
  const year = new Date().getUTCFullYear();
  const month = new Date().getUTCMonth();
  const values = [790, 980, 1010, 790, 825, 615, 650, 505, 330, 365, 605, 868];
  const monthly_energy = values.map((value, index) => {
    const date = new Date(Date.UTC(year, month - 11 + index, 1));
    return { month: date.toISOString().slice(0, 7), usable_hours: 720, p50_mwh: value };
  });
  const currentHour = new Date();
  currentHour.setUTCMinutes(0, 0, 0);
  const latestHour = currentHour.getTime() - 3600000;
  const latest = new Date(latestHour).toISOString();
  const lastSuccess = new Date(latestHour + 300000).toISOString();
  return {
    energy: {
      gross_energy_mwh: 9523, p50_mwh: 8333, p90_mwh: 7479,
      annualized_gross_mwh: 9600, annualized_p50_mwh: 8400, annualized_p90_mwh: 7539,
      usable_coverage_pct: 99.2, expected_hours: 8760, observed_hours: 8704, usable_hours: 8690,
      excluded_readings: { missing_speed: 8, nonnumeric_speed: 2, invalid_speed: 2, unsupported_unit: 1, off_hour: 1 },
      monthly_energy,
    },
    context: {
      site_name: "Spreewald", rated_power_mw: 3.6, latest_measurement_at: latest,
      last_success_at: lastSuccess, next_sync_at: new Date(currentHour.getTime() + 3600000).toISOString(), collection_healthy: true,
      inputs: { measurement_height_m: 100, hub_height_m: 140, shear_exponent: 0.20, availability_loss: 0.05, electrical_loss: 0.02, wake_loss: 0.06015, uncertainty: 0.08 },
      recent_measurements: [
        { timestamp: latest, wind_mast_ms: 7.8, wind_hub_ms: 8.6, power_mw: 2.9 },
        { timestamp: new Date(latestHour - 3600000).toISOString(), wind_mast_ms: 6.1, wind_hub_ms: 6.8, power_mw: 1.9 },
        { timestamp: new Date(latestHour - 7200000).toISOString(), wind_mast_ms: 4.3, wind_hub_ms: 4.8, power_mw: 0.8 },
      ],
      recent_runs: [
        { status: "succeeded", records_seen: 1, finished_at: lastSuccess },
        { status: "succeeded", records_seen: 2, finished_at: new Date(latestHour - 3600000).toISOString() },
        { status: "failed", error_summary: "Temporary ingestion timeout (auto-recovered)", finished_at: new Date(latestHour - 3840000).toISOString() },
      ],
    },
  };
}

function demoEnergyForPeriod(period) {
  if (period === "year") return demoData().energy;
  const start = period === "custom" ? $("start-date").value : utcDate(-Number(period));
  const end = period === "custom" ? $("end-date").value : utcDate();
  const first = new Date(`${start}T00:00:00Z`);
  const last = new Date(`${end}T00:00:00Z`);
  const days = Math.round((last - first) / 86400000);
  const totals = new Map();
  for (let index = 0; index < days; index++) {
    const day = new Date(first.getTime() + index * 86400000);
    const key = day.toISOString().slice(0, 7);
    const value = 20 + 5 * Math.cos((day.getUTCMonth() - 1) * Math.PI / 6);
    const current = totals.get(key) || { p50_mwh: 0, usable_hours: 0 };
    current.p50_mwh += value;
    current.usable_hours += 24;
    totals.set(key, current);
  }
  const monthly_energy = [...totals].map(([month, values]) => ({ month, ...values }));
  const p50 = monthly_energy.reduce((sum, point) => sum + point.p50_mwh, 0);
  const expected = days * 24;
  const usable = Math.round(expected * .992);
  return {
    gross_energy_mwh: p50 / (.95 * .98 * .93985), p50_mwh: p50, p90_mwh: p50 * .89744,
    usable_coverage_pct: expected ? 100 * usable / expected : 0,
    expected_hours: expected, observed_hours: Math.min(expected, usable + 1), usable_hours: usable,
    excluded_readings: { missing_speed: 1, nonnumeric_speed: 0, invalid_speed: 0, unsupported_unit: 0, off_hour: 0 },
    monthly_energy,
  };
}

async function loadEnergy() {
  const period = $("period-select").value;
  if (period === "custom" && (!$("start-date").value || !$("end-date").value || $("start-date").value >= $("end-date").value)) {
    setText("form-error", "Choose an end date later than the start date.");
    $("form-error").hidden = false;
    return;
  }
  if (period === "custom" && (new Date($("end-date").value) - new Date($("start-date").value)) > 732 * 86400000) {
    setText("form-error", "Choose a period of two years or less.");
    $("form-error").hidden = false;
    return;
  }
  $("form-error").hidden = true;
  if (activeRequest) activeRequest.abort();
  const controller = new AbortController();
  activeRequest = controller;
  const annual = period === "year";
  try {
    let data;
    if (demoMode) {
      data = demoEnergyForPeriod(period);
    } else {
      const url = new URL(annual ? "/energy/annual" : "/energy", location.origin);
      if (!annual) {
        const start = period === "custom" ? $("start-date").value : utcDate(-Number(period));
        const end = period === "custom" ? $("end-date").value : utcDate();
        url.searchParams.set("start", `${start}T00:00:00Z`);
        url.searchParams.set("end", `${end}T00:00:00Z`);
      }
      data = await getJson(url, controller.signal);
    }
    if (activeRequest !== controller) return;
    renderEnergy(data, annual);
    $("feedback").hidden = true;
  } catch (error) {
    if (activeRequest !== controller || error.name === "AbortError") return;
    showFeedback(`Energy data unavailable: ${error.message}`);
  } finally {
    if (activeRequest === controller) activeRequest = null;
  }
}
async function loadContext() {
  try {
    const data = demoMode ? demoData().context : await getJson("/dashboard/context");
    renderContext(data);
  } catch (error) {
    setStatus("Status unavailable", "unknown");
    setText("health-summary", `Collection data unavailable: ${error.message}`);
    renderMeasurements([]);
    renderRuns([]);
  }
}

$("period-select").addEventListener("change", () => {
  $("custom-form").hidden = $("period-select").value !== "custom";
  if ($("period-select").value !== "custom") loadEnergy();
});
$("custom-form").addEventListener("submit", (event) => { event.preventDefault(); loadEnergy(); });
function updateNavigation() {
  const section = location.hash === "#measurements" ? "measurements"
    : (["#operations", "#methodology"].includes(location.hash) ? "operations" : "overview");
  document.querySelectorAll(".top-nav a").forEach((link) => {
    const active = link.hash === `#${section}`;
    link.classList.toggle("is-active", active);
    if (active) link.setAttribute("aria-current", "location");
    else link.removeAttribute("aria-current");
  });
}
window.addEventListener("hashchange", updateNavigation);
updateNavigation();
$("start-date").value = utcDate(-30);
$("end-date").value = utcDate();
if (demoMode) {
  $("data-badge").hidden = false;
  setStatus("Demo preview", "demo");
}
loadContext();
loadEnergy();
