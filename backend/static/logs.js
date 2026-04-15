const params = new URLSearchParams(window.location.search);

const userIdEl = document.getElementById("userId");
const modeFilterEl = document.getElementById("modeFilter");
const fromDateEl = document.getElementById("fromDate");
const toDateEl = document.getElementById("toDate");
const searchTextEl = document.getElementById("searchText");
const pageSizeEl = document.getElementById("pageSize");
const logsBodyEl = document.getElementById("logsBody");
const pageInfoEl = document.getElementById("pageInfo");

const reloadBtn = document.getElementById("reloadBtn");
const clearBtn = document.getElementById("clearBtn");
const backBtn = document.getElementById("backBtn");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");

let currentPage = 1;
let totalPages = 1;
let modeChart;
let trendChart;

function readFilters() {
  return {
    mode: modeFilterEl.value,
    from_date: fromDateEl.value,
    to_date: toDateEl.value,
    search: searchTextEl.value.trim(),
  };
}

function writeFiltersToUrl(filters) {
  const p = new URLSearchParams();
  p.set("user_id", getUserId());
  if (filters.mode) p.set("mode", filters.mode);
  if (filters.from_date) p.set("from_date", filters.from_date);
  if (filters.to_date) p.set("to_date", filters.to_date);
  if (filters.search) p.set("search", filters.search);
  window.history.replaceState({}, "", `/logs.html?${p.toString()}`);
}

function getUserId() {
  return userIdEl.value.trim() || localStorage.getItem("nfc_user_id") || "demo-user";
}

function secToText(seconds) {
  const s = Math.max(0, Number(seconds || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m`;
}

function formatDate(val) {
  if (!val) return "-";
  const d = new Date(val);
  return d.toLocaleString();
}

function updateTable(items, page, pageSize) {
  logsBodyEl.innerHTML = "";
  if (!items.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = '<td colspan="6">No session logs found.</td>';
    logsBodyEl.appendChild(tr);
    return;
  }

  items.forEach((item, idx) => {
    const tr = document.createElement("tr");
    const number = (page - 1) * pageSize + idx + 1;
    const modeClass = `mode-${item.mode}`;

    tr.innerHTML = `
      <td>${number}</td>
      <td class="mode ${modeClass}">${item.mode}</td>
      <td>${formatDate(item.start_time)}</td>
      <td>${formatDate(item.end_time)}</td>
      <td>${secToText(item.duration_seconds)}</td>
      <td>${item.device_status || "-"}</td>
    `;
    logsBodyEl.appendChild(tr);
  });
}

function renderModeChart(modeTotals) {
  const ctx = document.getElementById("modeChart").getContext("2d");
  const values = [
    Number(modeTotals.study || 0) / 3600,
    Number(modeTotals.coding || 0) / 3600,
    Number(modeTotals.fun || 0) / 3600,
  ];

  if (modeChart) modeChart.destroy();
  modeChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Study", "Coding", "Fun"],
      datasets: [{
        data: values,
        backgroundColor: ["#2563eb", "#059669", "#ea580c"],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "Mode Total Hours" },
        legend: { position: "bottom" },
      },
    },
  });
}

function renderTrendChart(dailyBreakdown) {
  const ctx = document.getElementById("trendChart").getContext("2d");
  const labels = (dailyBreakdown || []).map((d) => d.date);
  const values = (dailyBreakdown || []).map((d) => Number(d.total_seconds || 0) / 3600);

  if (trendChart) trendChart.destroy();
  trendChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Hours",
        data: values,
        backgroundColor: "#0f766e",
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: { display: true, text: "Last 7 Days Trend" },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (v) => `${v}h`,
          },
        },
      },
    },
  });
}

async function loadLogs() {
  const userId = getUserId();
  const pageSize = Number(pageSizeEl.value || 20);
  const filters = readFilters();

  localStorage.setItem("nfc_user_id", userId);
  writeFiltersToUrl(filters);

  const qp = new URLSearchParams({
    user_id: userId,
    page: String(currentPage),
    page_size: String(pageSize),
  });
  if (filters.mode) qp.set("mode", filters.mode);
  if (filters.from_date) qp.set("from_date", filters.from_date);
  if (filters.to_date) qp.set("to_date", filters.to_date);
  if (filters.search) qp.set("search", filters.search);

  const url = `/api/logs?${qp.toString()}`;
  const res = await fetch(url, { cache: "no-store" });
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Failed to load logs");
  }

  totalPages = data.pagination.total_pages || 1;
  currentPage = data.pagination.page || 1;

  updateTable(data.items || [], currentPage, pageSize);
  renderModeChart(data.mode_totals_seconds || {});
  renderTrendChart(data.daily_breakdown || []);

  pageInfoEl.textContent = `Page ${currentPage} of ${totalPages} | Total sessions: ${data.pagination.total_items || 0}`;
  prevBtn.disabled = !data.pagination.has_prev;
  nextBtn.disabled = !data.pagination.has_next;
}

function init() {
  const userFromQuery = params.get("user_id") || localStorage.getItem("nfc_user_id") || "demo-user";
  userIdEl.value = userFromQuery;
  modeFilterEl.value = params.get("mode") || "";
  fromDateEl.value = params.get("from_date") || "";
  toDateEl.value = params.get("to_date") || "";
  searchTextEl.value = params.get("search") || "";

  reloadBtn.addEventListener("click", async () => {
    currentPage = 1;
    await loadLogs();
  });

  clearBtn.addEventListener("click", async () => {
    modeFilterEl.value = "";
    fromDateEl.value = "";
    toDateEl.value = "";
    searchTextEl.value = "";
    currentPage = 1;
    await loadLogs();
  });

  pageSizeEl.addEventListener("change", async () => {
    currentPage = 1;
    await loadLogs();
  });

  modeFilterEl.addEventListener("change", async () => {
    currentPage = 1;
    await loadLogs();
  });

  fromDateEl.addEventListener("change", async () => {
    currentPage = 1;
    await loadLogs();
  });

  toDateEl.addEventListener("change", async () => {
    currentPage = 1;
    await loadLogs();
  });

  searchTextEl.addEventListener("keydown", async (e) => {
    if (e.key !== "Enter") return;
    currentPage = 1;
    await loadLogs();
  });

  prevBtn.addEventListener("click", async () => {
    if (currentPage <= 1) return;
    currentPage -= 1;
    await loadLogs();
  });

  nextBtn.addEventListener("click", async () => {
    if (currentPage >= totalPages) return;
    currentPage += 1;
    await loadLogs();
  });

  backBtn.addEventListener("click", () => {
    window.location.href = `/select.html?user_id=${encodeURIComponent(getUserId())}`;
  });

  loadLogs().catch((err) => {
    logsBodyEl.innerHTML = `<tr><td colspan="6">Error: ${err.message}</td></tr>`;
    pageInfoEl.textContent = "Failed to load logs";
  });
}

init();
