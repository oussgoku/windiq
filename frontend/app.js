const $ = (id) => document.getElementById(id);
const form = $("energy-form");
const startInput = $("start-date");
const endInput = $("end-date");
const feedback = $("feedback");
const results = $("results");
const calculateButton = $("calculate-button");
let activeRequest;
let annualMode = true;

const integer = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const energy = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const percent = new Intl.NumberFormat("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

function utcDate(offsetDays = 0) {
  const date = new Date();
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

function setRange(days) {
  endInput.value = utcDate();
  if (days === "year") {
    const end = new Date(`${endInput.value}T00:00:00Z`);
    const year = end.getUTCFullYear() - 1;
    const month = end.getUTCMonth();
    const day = Math.min(end.getUTCDate(), new Date(Date.UTC(year, month + 1, 0)).getUTCDate());
    const start = new Date(Date.UTC(year, month, day));
    startInput.value = start.toISOString().slice(0, 10);
  } else {
    startInput.value = utcDate(-days);
  }
  annualMode = days === "year";
  document.querySelectorAll("[data-days]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.days === String(days));
  });
  $("form-error").hidden = true;
}

function showFeedback(message, kind = "info") {
  feedback.textContent = message;
  feedback.className = `feedback is-${kind}`;
  feedback.hidden = false;
}

function showFormError(message) {
  $("form-error").textContent = message;
  $("form-error").hidden = false;
}

function setText(id, value) {
  $(id).textContent = value;
}

function formatDate(dateString) {
  return new Intl.DateTimeFormat("en-US", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${dateString}T00:00:00Z`));
}

function formatMonth(month) {
  return new Intl.DateTimeFormat("en-US", { month: "short", year: "2-digit", timeZone: "UTC" }).format(new Date(`${month}-01T00:00:00Z`));
}

function formatHour(timestamp) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "2-digit", hourCycle: "h23", timeZone: "UTC" }).format(new Date(timestamp));
}

function renderMonthlyChart(points) {
  const chart = $("monthly-chart");
  chart.replaceChildren();
  chart.style.setProperty("--bar-count", String(points.length));
  const maximum = Math.max(0, ...points.map((point) => point.p50_mwh));
  for (const point of points) {
    const column = document.createElement("div");
    column.className = "bar-column";
    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = point.usable_hours ? energy.format(point.p50_mwh) : "—";
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("span");
    fill.className = "bar-fill";
    fill.style.height = maximum ? `${(point.p50_mwh / maximum) * 100}%` : "0%";
    track.append(fill);
    const label = document.createElement("span");
    label.className = "bar-label";
    label.textContent = formatMonth(point.month);
    column.append(value, track, label);
    chart.append(column);
  }
  chart.setAttribute("aria-label", points.map((point) => `${formatMonth(point.month)}: ${point.usable_hours ? `${energy.format(point.p50_mwh)} MWh P50 from ${point.usable_hours} usable hours` : "no usable measurements"}`).join("; "));
}

function svgElement(name, attributes) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  return element;
}

function renderWindChart(points) {
  const chart = $("wind-chart");
  chart.replaceChildren();
  const speeds = points.map((point) => Number.isFinite(point.wind_speed_ms) ? point.wind_speed_ms : null);
  const valid = speeds.filter((speed) => speed !== null);
  const peak = Math.max(0, ...valid);
  const scale = Math.max(5, Math.ceil(peak / 5) * 5);
  setText("wind-max", String(scale));
  setText("wind-mid", String(scale / 2));
  setText("wind-start", points.length ? formatHour(points[0].timestamp) : "—");
  setText("wind-end", points.length ? formatHour(points.at(-1).timestamp) : "—");
  setText("wind-summary", valid.length ? `${valid.length} / ${points.length} hours · peak ${percent.format(peak)} m/s` : "No usable readings");
  for (const y of [12, 100, 188]) chart.append(svgElement("line", { x1: 0, y1: y, x2: 800, y2: y, class: "wind-grid" }));
  let path = "";
  let connected = false;
  speeds.forEach((speed, index) => {
    if (speed === null) {
      connected = false;
      return;
    }
    const x = points.length === 1 ? 400 : (index / (points.length - 1)) * 800;
    const y = 188 - (speed / scale) * 176;
    path += `${connected ? " L" : " M"}${x.toFixed(2)} ${y.toFixed(2)}`;
    chart.append(svgElement("circle", { cx: x, cy: y, r: 1.6, class: "wind-point" }));
    connected = true;
  });
  chart.append(svgElement("path", { d: path, class: "wind-line" }));
  chart.setAttribute("aria-label", `${valid.length} usable hourly wind speeds in ${points.length} hours. Peak ${percent.format(peak)} metres per second. Gaps mark missing or invalid readings.`);
}

function renderCharts(data) {
  const available = Array.isArray(data.monthly_energy) && Array.isArray(data.wind_7d);
  $("charts-content").hidden = !available;
  $("charts-unavailable").hidden = available;
  if (!available) return;
  renderMonthlyChart(data.monthly_energy);
  renderWindChart(data.wind_7d);
}

function renderResult(data, startDate, endDate, annual) {
  const excluded = data.excluded_readings;
  const usableCoverage = Number(data.usable_coverage_pct);
  setText("result-period", `${formatDate(annual ? data.window_start.slice(0, 10) : startDate)} – ${formatDate(annual ? data.window_end.slice(0, 10) : endDate)} · End exclusive · UTC`);
  setText("mast-id", `Mast ${data.mast_id}`);
  setText("p50-label", annual ? "Net AEP · P50" : "Net energy · P50");
  setText("p90-label", annual ? "AEP · P90" : "Conservative · P90");
  setText("gross-label", annual ? "Gross AEP" : "Gross energy");
  const display = (value) => value === null ? "—" : energy.format(value);
  setText("p50-value", display(annual ? data.annualized_p50_mwh : data.p50_mwh));
  setText("p90-value", display(annual ? data.annualized_p90_mwh : data.p90_mwh));
  setText("gross-value", display(annual ? data.annualized_gross_mwh : data.gross_energy_mwh));
  setText("method-note", annual
    ? `Annual estimates scale the energy from ${integer.format(data.usable_hours)} usable hours to ${integer.format(data.expected_hours)} expected hours (factor ${data.annualization_factor === null ? "unavailable" : data.annualization_factor.toFixed(3)}). This assumes missing hours resemble measured hours; low coverage makes the estimate less reliable. Monthly bars show observed energy only.`
    : "Estimates use only valid observed hourly measurements in the selected period. Missing hours are not filled in, and these values are not extrapolated to a full year.");
  setText("usable-coverage", `${percent.format(usableCoverage)}%`);
  setText("expected-hours", integer.format(data.expected_hours));
  setText("observed-hours", integer.format(data.observed_hours));
  setText("usable-hours", integer.format(data.usable_hours));
  setText("missing-speed", integer.format(excluded.missing_speed));
  setText("nonnumeric-speed", integer.format(excluded.nonnumeric_speed));
  setText("invalid-speed", integer.format(excluded.invalid_speed));
  setText("unsupported-unit", integer.format(excluded.unsupported_unit));
  setText("off-hour", integer.format(excluded.off_hour));
  $("coverage-fill").style.width = `${Math.max(0, Math.min(100, usableCoverage))}%`;
  $("coverage-visual").setAttribute("aria-label", `${percent.format(usableCoverage)}% usable coverage`);
  setText("coverage-note", `${percent.format(data.observed_coverage_pct)}% of expected hours have a stored reading; ${percent.format(usableCoverage)}% could be used for energy calculations.`);
  renderCharts(data);
  results.hidden = false;
}

function errorDetail(response, body) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || "Invalid request").join("; ");
  return `The API returned HTTP ${response.status}.`;
}

async function loadEnergy() {
  $("form-error").hidden = true;
  if (!startInput.value || !endInput.value) {
    showFormError("Choose both a start date and an end date.");
    return;
  }
  if (endInput.value <= startInput.value) {
    showFormError("The end date must be later than the start date.");
    return;
  }

  const startDate = startInput.value;
  const endDate = endInput.value;
  const requestAnnual = annualMode;

  if (activeRequest) activeRequest.abort();
  const controller = new AbortController();
  activeRequest = controller;
  const timeout = setTimeout(() => controller.abort(), 20000);
  calculateButton.disabled = true;
  calculateButton.querySelector("span:first-child").textContent = "Calculating…";
  results.hidden = true;
  showFeedback("Loading measurements and calculating energy…", "loading");

  try {
    const url = new URL(requestAnnual ? "/energy/annual" : "/energy", window.location.origin);
    if (!requestAnnual) {
      url.searchParams.set("start", `${startDate}T00:00:00Z`);
      url.searchParams.set("end", `${endDate}T00:00:00Z`);
    }
    const response = await fetch(url, { signal: controller.signal });
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(errorDetail(response, body));
    if (!body || !body.excluded_readings || typeof body.p50_mwh !== "number") {
      throw new Error("The API returned an unexpected energy response.");
    }
    renderResult(body, startDate, endDate, requestAnnual);
    feedback.hidden = true;
  } catch (error) {
    if (activeRequest !== controller) return;
    let message = error.message;
    if (error.name === "AbortError") message = "The request timed out. Check the API and try again.";
    if (error instanceof TypeError) message = "Could not reach the API. Please try again shortly.";
    showFeedback(message, "error");
  } finally {
    clearTimeout(timeout);
    if (activeRequest === controller) {
      activeRequest = null;
      calculateButton.disabled = false;
      calculateButton.querySelector("span:first-child").textContent = "Calculate energy";
    }
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  loadEnergy();
});

document.querySelectorAll("[data-days]").forEach((button) => {
  button.addEventListener("click", () => setRange(button.dataset.days === "year" ? "year" : Number(button.dataset.days)));
});

for (const input of [startInput, endInput]) {
  input.addEventListener("input", () => {
    annualMode = false;
    $("form-error").hidden = true;
    document.querySelectorAll("[data-days]").forEach((button) => button.classList.remove("is-active"));
  });
}

setRange("year");
loadEnergy();
