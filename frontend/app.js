const $ = (id) => document.getElementById(id);
const demoMode = new URLSearchParams(location.search).get("demo") === "1";
const translations = {
  de: {
    brand: "WindIQ Übersicht", navigation: "Hauptnavigation", languageLabel: "Sprache wählen",
    overview: "Übersicht", measurements: "Messwerte", operations: "Betrieb", checkingStatus: "Status wird geprüft",
    pageTitle: "Energieertrag im Überblick", referenceTurbine: "Referenzturbine", timePeriod: "Zeitraum",
    last12Months: "Letzte 12 Monate", last30Days: "Letzte 30 Tage", last7Days: "Letzte 7 Tage", customPeriod: "Eigener Zeitraum",
    startDate: "Startdatum", endDate: "Enddatum", applyPeriod: "Zeitraum anwenden", dateHint: "UTC-Daten · Enddatum ausgeschlossen",
    collectionTimes: "Erfassungszeiten", lastMeasurement: "Letzter Messwert:", summaryLabel: "Ertrag und Datenabdeckung",
    grossTooltip: "Vor Standortverlusten", p50Tooltip: "Nach Verfügbarkeits-, elektrischen und Nachlaufverlusten",
    p90Tooltip: "P50 mit Unsicherheit angepasst", dataCoverage: "Datenabdeckung", coverageTooltip: "Nutzbare Messstunden geteilt durch erwartete Stunden",
    coveragePlaceholder: "— nutzbare Stunden", monthlyChart: "Monatlicher beobachteter Nettoertrag",
    monthlyEnergy: "Monatlicher Ertrag", calculationInputs: "Berechnungsparameter", measurementHeight: "Messhöhe", hubHeight: "Nabenhöhe",
    windShear: "Windscherung α", availabilityLoss: "Verfügbarkeitsverlust", electricalLoss: "Elektrischer Verlust",
    wakeLoss: "Nachlaufverlust", uncertainty: "Unsicherheit", recentMeasurements: "Letzte Messwerte", timesUTC: "Zeiten in UTC",
    timeUTC: "Zeit (UTC)", windMast: "Wind am Mast", windHub: "Wind an der Nabe", power: "Leistung",
    loadingMeasurements: "Messwerte werden geladen…", collectionHealth: "Datenerfassung", loadingHistory: "Verlauf wird geladen…",
    recentHistory: "Letzte Ereignisse", methodologyQuality: "Methodik und Datenqualität", expectedHours: "Erwartete Stunden",
    observedHours: "Erfasste Stunden", usableHours: "Nutzbare Stunden", excludedReadings: "Ausgeschlossene Messwerte",
    footerNote: "Stündliche Messwerte · Gleitender Zeitraum · Zeiten in UTC", methodologyLink: "Methodik ↗",
    noMonthly: "Keine monatlichen Messwerte verfügbar.", barTitle: "{month}: {energy} MWh aus {hours} nutzbaren Stunden",
    barAria: "{month}: {energy} MWh beobachteter Nettoertrag", incompleteEnergy: "Die Ertragsdaten sind unvollständig.",
    grossAnnual: "Brutto-AEP", grossPeriod: "Bruttoertrag", p50Annual: "Netto-AEP · P50", p50Period: "Nettoertrag · P50",
    p90Annual: "P90", p90Period: "P90-Ertrag", grossAnnualNote: "Beobachtet · vor Verlusten",
    grossPeriodNote: "Beobachteter Zeitraum · vor Verlusten", p50AnnualNote: "Beobachtet · nach Verlusten",
    p50PeriodNote: "Beobachteter Zeitraum · nach Verlusten", p90AnnualNote: "Beobachtet · P90",
    p90PeriodNote: "Beobachteter Zeitraum mit Unsicherheit", coverageNote: "{usable} / {expected} nutzbare Stunden",
    exclusionNote: "Ausgeschlossen: {missing} fehlend, {nonnumeric} nicht numerisch, {invalid} ungültig, {unit} nicht unterstützte Einheiten, {offhour} außerhalb voller Stunden.",
    partialMonths: " Der gleitende Zeitraum berührt 13 Kalendermonate; der erste und letzte Monat sind unvollständig.",
    monthlyPartial: "Beobachtete MWh · Teilmonate", monthlyObserved: "Beobachteter Nettoertrag · MWh",
    annualMethod: "Die AEP-Karten summieren den Ertrag aus {usable} nutzbaren Stunden der letzten 12 Monate. Fehlende Stunden werden nicht ergänzt. Die Monatsbalken zeigen ebenfalls den beobachteten Nettoertrag.{partial}",
    annualizedMethod: "Zusätzliche Hochrechnung auf {expected} Stunden (Annahme: fehlende Stunden ähneln nutzbaren Stunden): Brutto {gross} MWh · P50 {p50} MWh · P90 {p90} MWh.",
    annualizedUnavailable: "Eine Hochrechnung ist ohne nutzbare Messstunden nicht möglich.",
    periodMethod: "Diese Werte summieren nur nutzbare stündliche Messungen im gewählten UTC-Zeitraum. Fehlende Stunden werden nicht ergänzt; die Monatsbalken zeigen den beobachteten Nettoertrag.",
    noMeasurements: "Noch keine Messwerte verfügbar.", noRuns: "Noch keine Erfassungsläufe vorhanden.",
    sampleRun: "Beispieldaten geladen · {count} Datensätze", sampleRunOne: "Beispieldaten geladen · 1 Datensatz",
    succeededRun: "Erfassung erfolgreich · {count} Datensätze vom API erhalten", succeededRunOne: "Erfassung erfolgreich · 1 Datensatz vom API erhalten",
    viewAllRuns: "Alle Läufe anzeigen", hideAllRuns: "Verlauf schließen", allRuns: "Alle Erfassungsläufe",
    loadMoreRuns: "Weitere laden", loadingRuns: "Läufe werden geladen…", runsUnavailable: "Läufe konnten nicht geladen werden: {error}",
    demoTimeout: "Vorübergehende Zeitüberschreitung bei der Datenerfassung (automatisch behoben)",
    failedRun: "Erfassung {status}{error}", statusSucceeded: "erfolgreich", statusFailed: "fehlgeschlagen", statusRunning: "läuft",
    fixtureBadge: "Lokale API · Beispieldaten", demoBadge: "Demo-Vorschau · Beispieldaten", windSite: "Windpark", fixtureSite: "Lokaler Teststandort",
    sampleLoaded: "Beispieldaten geladen:", lastSuccessfulSync: "Letzte erfolgreiche Synchronisierung:", scheduler: "Zeitplan:",
    nextScheduledSync: "Nächste Synchronisierung:", schedulerOff: "Im Testmodus nicht aktiv", demoPreview: "Demo-Vorschau",
    localTestData: "Lokale Testdaten", operational: "Betriebsbereit", needsAttention: "Handlungsbedarf",
    testMode: "Testmodus · Datenerfassung nicht aktiv", latestSyncSucceeded: "Letzte Synchronisierung erfolgreich",
    collectionNeedsAttention: "Datenerfassung erfordert Aufmerksamkeit", statusUnavailable: "Status nicht verfügbar",
    collectionUnavailable: "Erfassungsdaten nicht verfügbar: {error}", energyUnavailable: "Ertragsdaten nicht verfügbar: {error}",
    lastChecked: "Zuletzt geprüft: {time}",
    invalidDateOrder: "Das Enddatum muss nach dem Startdatum liegen.", periodTooLong: "Wählen Sie einen Zeitraum von höchstens zwei Jahren."
  },
  en: {
    brand: "WindIQ overview", navigation: "Main navigation", languageLabel: "Choose language",
    overview: "Overview", measurements: "Measurements", operations: "Operations", checkingStatus: "Checking status",
    pageTitle: "Energy yield overview", referenceTurbine: "Reference turbine", timePeriod: "Time period",
    last12Months: "Last 12 months", last30Days: "Last 30 days", last7Days: "Last 7 days", customPeriod: "Custom period",
    startDate: "Start date", endDate: "End date", applyPeriod: "Apply period", dateHint: "UTC dates · end date excluded",
    collectionTimes: "Collection times", lastMeasurement: "Last measurement:", summaryLabel: "Energy and coverage summary",
    grossTooltip: "Before site losses", p50Tooltip: "After availability, electrical, and wake losses",
    p90Tooltip: "P50 adjusted for uncertainty", dataCoverage: "Data coverage", coverageTooltip: "Usable measurement hours divided by expected hours",
    coveragePlaceholder: "— usable hours", monthlyChart: "Monthly observed net energy",
    monthlyEnergy: "Monthly energy", calculationInputs: "Calculation inputs", measurementHeight: "Measurement height", hubHeight: "Hub height",
    windShear: "Wind shear α", availabilityLoss: "Availability loss", electricalLoss: "Electrical loss",
    wakeLoss: "Wake loss", uncertainty: "Uncertainty", recentMeasurements: "Recent measurements", timesUTC: "Times in UTC",
    timeUTC: "Time (UTC)", windMast: "Wind at mast", windHub: "Wind at hub", power: "Power",
    loadingMeasurements: "Loading measurements…", collectionHealth: "Collection health", loadingHistory: "Loading collection history…",
    recentHistory: "Recent history", methodologyQuality: "Methodology and data quality", expectedHours: "Expected hours",
    observedHours: "Observed hours", usableHours: "Usable hours", excludedReadings: "Excluded readings",
    footerNote: "Hourly measurements · Rolling period · Times in UTC", methodologyLink: "Methodology ↗",
    noMonthly: "No monthly measurements available.", barTitle: "{month}: {energy} MWh from {hours} usable hours",
    barAria: "{month}: {energy} MWh observed net energy", incompleteEnergy: "The energy response is incomplete.",
    grossAnnual: "Gross AEP", grossPeriod: "Gross energy", p50Annual: "Net AEP · P50", p50Period: "Net energy · P50",
    p90Annual: "P90", p90Period: "P90 energy", grossAnnualNote: "Observed · before losses",
    grossPeriodNote: "Observed period · before losses", p50AnnualNote: "Observed · after losses",
    p50PeriodNote: "Observed period · after losses", p90AnnualNote: "Observed · P90",
    p90PeriodNote: "Observed period with uncertainty", coverageNote: "{usable} / {expected} usable hours",
    exclusionNote: "Excluded: {missing} missing, {nonnumeric} nonnumeric, {invalid} invalid, {unit} unsupported units, {offhour} off-hour.",
    partialMonths: " The rolling window touches 13 calendar months, with partial first and last months.",
    monthlyPartial: "Observed MWh · partial months", monthlyObserved: "Observed net energy · MWh",
    annualMethod: "The AEP cards sum energy from {usable} usable hours in the last 12 months. Missing hours are not filled in. Monthly bars also show observed net energy.{partial}",
    annualizedMethod: "Additional estimate scaled to {expected} hours (assuming missing hours resemble usable hours): gross {gross} MWh · P50 {p50} MWh · P90 {p90} MWh.",
    annualizedUnavailable: "An annualized estimate is unavailable without usable measurements.",
    periodMethod: "These figures sum only usable hourly measurements in the selected UTC window. Missing hours are not filled in; monthly bars show observed net energy.",
    noMeasurements: "No measurements available yet.", noRuns: "No collection runs recorded yet.",
    sampleRun: "Sample data loaded · {count} records", sampleRunOne: "Sample data loaded · 1 record",
    succeededRun: "Collection succeeded · {count} records seen", succeededRunOne: "Collection succeeded · 1 record seen",
    viewAllRuns: "View all runs", hideAllRuns: "Hide run history", allRuns: "All collection runs",
    loadMoreRuns: "Load more", loadingRuns: "Loading runs…", runsUnavailable: "Could not load runs: {error}",
    demoTimeout: "Temporary ingestion timeout (auto-recovered)",
    failedRun: "Collection {status}{error}", statusSucceeded: "succeeded", statusFailed: "failed", statusRunning: "running",
    fixtureBadge: "Local API · Sample data", demoBadge: "Demo preview · Sample data", windSite: "Wind site", fixtureSite: "Local test fixture",
    sampleLoaded: "Sample loaded:", lastSuccessfulSync: "Last successful sync:", scheduler: "Scheduler:",
    nextScheduledSync: "Next scheduled sync:", schedulerOff: "Not running in test mode", demoPreview: "Demo preview",
    localTestData: "Local test data", operational: "Operational", needsAttention: "Needs attention",
    testMode: "Test mode · ingestion is not running", latestSyncSucceeded: "Latest sync succeeded",
    collectionNeedsAttention: "Collection needs attention", statusUnavailable: "Status unavailable",
    collectionUnavailable: "Collection data unavailable: {error}", energyUnavailable: "Energy data unavailable: {error}",
    lastChecked: "Last checked: {time}",
    invalidDateOrder: "Choose an end date later than the start date.", periodTooLong: "Choose a period of two years or less."
  }
};
let language = "de";
try { language = localStorage.getItem("windiq-language") === "en" ? "en" : "de"; } catch { /* Private storage can be unavailable. */ }
let number, oneDecimal, twoDecimals, lossPercent;
let latestEnergy, latestContext, latestEnergyAnnual;
let energyError, contextError, formErrorKey;
let activeRequest;
let lastContextCheckAt, contextRequestId = 0;
let allRuns = [], nextRunCursor = null, allRunsOpen = false, allRunsLoading = false, allRunsError = null, allRunsRequestId = 0;

function t(key, values = {}) {
  return translations[language][key].replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? ""));
}
function formatters() {
  const locale = language === "de" ? "de-DE" : "en-US";
  number = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  oneDecimal = new Intl.NumberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  twoDecimals = new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  lossPercent = new Intl.NumberFormat(locale, { maximumFractionDigits: 3 });
}
function setLanguage(nextLanguage) {
  language = nextLanguage === "en" ? "en" : "de";
  try { localStorage.setItem("windiq-language", language); } catch { /* The switch still works for this page. */ }
  formatters();
  document.documentElement.lang = language;
  document.title = `WindIQ | ${t("pageTitle")}`;
  document.querySelector('meta[name="description"]').content = language === "de"
    ? "WindIQ Dashboard für Windertrag und Datenerfassung." : "WindIQ wind energy and data collection dashboard.";
  document.querySelectorAll("[data-i18n]").forEach((node) => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll("[data-i18n-aria]").forEach((node) => { node.setAttribute("aria-label", t(node.dataset.i18nAria)); });
  document.querySelectorAll("[data-i18n-title]").forEach((node) => { node.title = t(node.dataset.i18nTitle); });
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.language === language));
  });
  if (latestContext) renderContext(latestContext);
  if (latestEnergy) renderEnergy(latestEnergy, latestEnergyAnnual);
  if (energyError) showFeedback(t("energyUnavailable", { error: energyError }));
  if (contextError) renderContextError(contextError);
  renderAllRuns();
  renderCheckedAt();
  if (formErrorKey) setText("form-error", t(formErrorKey));
}

function setText(id, value) { $(id).textContent = value; }
function renderCheckedAt() {
  setText("status-checked", lastContextCheckAt ? t("lastChecked", { time: dateTime(lastContextCheckAt) }) : "");
}
function utcDate(offsetDays = 0) {
  const date = new Date();
  date.setUTCHours(0, 0, 0, 0);
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}
function dateTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(language === "de" ? "de-DE" : "en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "UTC" }).format(new Date(value)) + " UTC";
}
function timeOnly(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(language === "de" ? "de-DE" : "en-GB", { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "UTC" }).format(new Date(value)) + " UTC";
}
function monthLabel(value) {
  const parts = new Intl.DateTimeFormat(language === "de" ? "de-DE" : "en-GB", { month: "short", year: "numeric", timeZone: "UTC" }).formatToParts(new Date(`${value}-01T00:00:00Z`));
  return { month: parts.find((part) => part.type === "month").value, year: parts.find((part) => part.type === "year").value };
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
  const response = await fetch(url, { signal, cache: "no-store" });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorDetail(response, body));
  return body;
}

function renderMonthly(points) {
  const chart = $("monthly-chart");
  chart.replaceChildren();
  if (!Array.isArray(points) || !points.length) {
    chart.textContent = t("noMonthly");
    chart.setAttribute("aria-label", t("noMonthly"));
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
    const month = monthLabel(point.month);
    bar.title = t("barTitle", { month: `${month.month} ${month.year}`, energy: number.format(point.p50_mwh), hours: number.format(point.usable_hours) });
    const label = document.createElement("span");
    label.className = "month-label";
    const monthName = document.createElement("span");
    monthName.textContent = month.month;
    const year = document.createElement("small");
    year.textContent = month.year;
    label.append(monthName, year);
    item.append(bar, label);
    chart.append(item);
  }
  chart.setAttribute("aria-label", points.map((point) => {
    const month = monthLabel(point.month);
    return t("barAria", { month: `${month.month} ${month.year}`, energy: number.format(point.p50_mwh) });
  }).join("; "));
}

function renderEnergy(data, annual) {
  if (!data || typeof data.p50_mwh !== "number") throw new Error(t("incompleteEnergy"));
  setText("gross-label", t(annual ? "grossAnnual" : "grossPeriod"));
  setText("p50-label", t(annual ? "p50Annual" : "p50Period"));
  setText("p90-label", t(annual ? "p90Annual" : "p90Period"));
  setText("gross-value", displayEnergy(data.gross_energy_mwh));
  setText("p50-value", displayEnergy(data.p50_mwh));
  setText("p90-value", displayEnergy(data.p90_mwh));
  setText("gross-note", t(annual ? "grossAnnualNote" : "grossPeriodNote"));
  setText("p50-note", t(annual ? "p50AnnualNote" : "p50PeriodNote"));
  setText("p90-note", t(annual ? "p90AnnualNote" : "p90PeriodNote"));
  setText("coverage-value", `${oneDecimal.format(data.usable_coverage_pct)}%`);
  setText("coverage-note", t("coverageNote", { usable: number.format(data.usable_hours), expected: number.format(data.expected_hours) }));
  setText("expected-hours", number.format(data.expected_hours));
  setText("observed-hours", number.format(data.observed_hours));
  setText("usable-hours", number.format(data.usable_hours));
  const excluded = data.excluded_readings || {};
  const excludedCount = Object.values(excluded).reduce((sum, value) => sum + (Number(value) || 0), 0);
  setText("excluded-hours", number.format(excludedCount));
  setText("exclusion-note", t("exclusionNote", { missing: number.format(excluded.missing_speed || 0), nonnumeric: number.format(excluded.nonnumeric_speed || 0), invalid: number.format(excluded.invalid_speed || 0), unit: number.format(excluded.unsupported_unit || 0), offhour: number.format(excluded.off_hour || 0) }));
  const partialMonths = annual && data.monthly_energy?.length > 12
    ? t("partialMonths")
    : "";
  setText("monthly-aside", t(partialMonths ? "monthlyPartial" : "monthlyObserved"));
  setText("method-note", annual
    ? t("annualMethod", { usable: number.format(data.usable_hours), partial: partialMonths })
    : t("periodMethod"));
  $("annualized-note").hidden = !annual;
  if (annual) {
    setText("annualized-note", data.annualization_factor == null
      ? t("annualizedUnavailable")
      : t("annualizedMethod", {
        expected: number.format(data.expected_hours),
        gross: number.format(data.annualized_gross_mwh),
        p50: number.format(data.annualized_p50_mwh),
        p90: number.format(data.annualized_p90_mwh),
      }));
  }
  renderMonthly(data.monthly_energy);
}

function renderMeasurements(rows) {
  const body = $("measurements-body");
  body.replaceChildren();
  if (!rows?.length) {
    const row = body.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 4;
    cell.textContent = t("noMeasurements");
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
function renderRuns(runs, fixtureMode = false, listId = "run-history", showAll = false) {
  const list = $(listId);
  list.replaceChildren();
  if (!runs?.length) {
    const item = document.createElement("li");
    item.textContent = t("noRuns");
    list.append(item);
    return;
  }
  for (const run of showAll ? runs : runs.slice(0, 3)) {
    const item = document.createElement("li");
    item.className = `run-item is-${fixtureMode ? "fixture" : run.status}`;
    const icon = document.createElement("span");
    icon.className = "run-icon";
    icon.textContent = fixtureMode ? "i" : (run.status === "succeeded" ? "✓" : "!");
    const description = document.createElement("span");
    const status = run.status || "unknown";
    const statusKey = `status${status[0].toUpperCase()}${status.slice(1)}`;
    const errorText = run.error_key === "demoTimeout" ? t("demoTimeout") : run.error_summary;
    description.textContent = fixtureMode
      ? t(run.records_seen === 1 ? "sampleRunOne" : "sampleRun", { count: number.format(run.records_seen) })
      : (run.status === "succeeded" ? t(run.records_seen === 1 ? "succeededRunOne" : "succeededRun", { count: number.format(run.records_seen) })
        : t("failedRun", { status: translations[language][statusKey] || status, error: errorText ? ` · ${errorText}` : "" }));
    const time = document.createElement("time");
    time.textContent = fixtureMode || showAll ? dateTime(run.finished_at || run.started_at) : timeOnly(run.finished_at || run.started_at);
    item.append(icon, description, time);
    list.append(item);
  }
}
function renderAllRuns() {
  setText("view-all-runs", t(allRunsOpen ? "hideAllRuns" : "viewAllRuns"));
  if (!allRunsOpen) return;
  if (allRunsLoading && !allRuns.length) {
    setText("all-runs", t("loadingRuns"));
  } else {
    renderRuns(allRuns, latestContext?.data_mode === "fixture", "all-runs", true);
  }
  $("all-runs-error").hidden = !allRunsError;
  if (allRunsError) setText("all-runs-error", t("runsUnavailable", { error: allRunsError }));
  $("load-more-runs").hidden = nextRunCursor === null;
  $("load-more-runs").disabled = allRunsLoading;
  setText("load-more-runs", t(allRunsLoading ? "loadingRuns" : "loadMoreRuns"));
}
async function loadRunPage(reset = false) {
  if (allRunsLoading) return;
  const requestId = ++allRunsRequestId;
  allRunsLoading = true;
  allRunsError = null;
  if (reset) { allRuns = []; nextRunCursor = null; }
  renderAllRuns();
  try {
    const data = demoMode
      ? { runs: demoData().context.recent_runs, next_before_id: null }
      : await getJson(`/ingestion/runs?limit=20${nextRunCursor === null ? "" : `&before_id=${nextRunCursor}`}`);
    if (requestId !== allRunsRequestId) return;
    allRuns.push(...data.runs);
    nextRunCursor = data.next_before_id;
  } catch (error) {
    if (requestId !== allRunsRequestId) return;
    allRunsError = error.message;
  } finally {
    if (requestId === allRunsRequestId) {
      allRunsLoading = false;
      renderAllRuns();
    }
  }
}
function renderContext(data) {
  const fixtureMode = data.data_mode === "fixture";
  $("data-badge").hidden = !fixtureMode && !demoMode;
  if (fixtureMode || demoMode) setText("data-badge", t(demoMode ? "demoBadge" : "fixtureBadge"));
  setText("site-name", fixtureMode && data.site_name === "Local test fixture" ? t("fixtureSite") : (data.site_name || data.mast_id || t("windSite")));
  setText("rated-power", oneDecimal.format(data.rated_power_mw));
  setText("last-measurement", dateTime(data.latest_measurement_at));
  setText("last-sync-caption", t(fixtureMode ? "sampleLoaded" : "lastSuccessfulSync"));
  setText("last-sync", fixtureMode ? dateTime(data.last_success_at) : timeOnly(data.last_success_at));
  setText("next-sync-caption", t(fixtureMode ? "scheduler" : "nextScheduledSync"));
  setText("next-sync", fixtureMode ? t("schedulerOff") : timeOnly(data.next_sync_at));
  setStatus(t(demoMode ? "demoPreview" : (fixtureMode ? "localTestData" : (data.collection_healthy ? "operational" : "needsAttention"))), demoMode || fixtureMode ? "demo" : (data.collection_healthy ? "healthy" : "warning"));
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
  message.textContent = t(fixtureMode ? "testMode" : (healthy ? "latestSyncSucceeded" : "collectionNeedsAttention"));
  const time = document.createElement("time");
  time.textContent = fixtureMode ? "" : timeOnly(data.last_success_at);
  line.append(icon, message, time);
  $("health-summary").append(line);
  renderMeasurements(data.recent_measurements);
  renderRuns(data.recent_runs, fixtureMode);
}
function renderContextError(error) {
  setStatus(t("statusUnavailable"), "unknown");
  setText("last-measurement", "—");
  setText("last-sync", "—");
  setText("next-sync", "—");
  setText("health-summary", t("collectionUnavailable", { error }));
  renderMeasurements([]);
  renderRuns([]);
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
        { status: "failed", error_key: "demoTimeout", finished_at: new Date(latestHour - 3840000).toISOString() },
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
    formErrorKey = "invalidDateOrder";
    setText("form-error", t(formErrorKey));
    $("form-error").hidden = false;
    return;
  }
  if (period === "custom" && (new Date($("end-date").value) - new Date($("start-date").value)) > 732 * 86400000) {
    formErrorKey = "periodTooLong";
    setText("form-error", t(formErrorKey));
    $("form-error").hidden = false;
    return;
  }
  $("form-error").hidden = true;
  formErrorKey = null;
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
    latestEnergy = data;
    latestEnergyAnnual = annual;
    energyError = null;
    $("feedback").hidden = true;
  } catch (error) {
    if (activeRequest !== controller || error.name === "AbortError") return;
    energyError = error.message;
    showFeedback(t("energyUnavailable", { error: energyError }));
  } finally {
    if (activeRequest === controller) activeRequest = null;
  }
}
async function loadContext() {
  const requestId = ++contextRequestId;
  try {
    const data = demoMode ? demoData().context : await getJson("/dashboard/context");
    if (requestId !== contextRequestId) return;
    lastContextCheckAt = Date.now();
    renderContext(data);
    latestContext = data;
    contextError = null;
  } catch (error) {
    if (requestId !== contextRequestId) return;
    lastContextCheckAt = Date.now();
    latestContext = null;
    contextError = error.message;
    renderContextError(contextError);
  }
  renderCheckedAt();
}

$("period-select").addEventListener("change", () => {
  $("custom-form").hidden = $("period-select").value !== "custom";
  if ($("period-select").value !== "custom") loadEnergy();
});
$("custom-form").addEventListener("submit", (event) => { event.preventDefault(); loadEnergy(); });
$("view-all-runs").addEventListener("click", () => {
  allRunsOpen = !allRunsOpen;
  $("all-runs-panel").hidden = !allRunsOpen;
  $("view-all-runs").setAttribute("aria-expanded", String(allRunsOpen));
  if (allRunsOpen) loadRunPage(true);
  else { ++allRunsRequestId; allRunsLoading = false; }
  renderAllRuns();
});
$("load-more-runs").addEventListener("click", () => loadRunPage());
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
document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.language));
});
setLanguage(language);
if (demoMode) {
  $("data-badge").hidden = false;
  setText("data-badge", t("demoBadge"));
  setStatus(t("demoPreview"), "demo");
}
loadContext();
loadEnergy();
if (!demoMode) {
  setInterval(() => { if (!document.hidden) loadContext(); }, 5 * 60 * 1000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && (!lastContextCheckAt || Date.now() - lastContextCheckAt > 60 * 1000)) loadContext();
  });
}
