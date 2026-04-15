// NFC Productivity Widget for Scriptable
// Set these values before first run.
const API_BASE = "https://nfcproject-idfake3097-nyflbcxb.leapcell.dev";
const USER_ID = "bhavneet";
const REFRESH_MINUTES = 2;

function toHms(totalSeconds) {
  const s = Math.max(0, Number(totalSeconds || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m`;
}

function pct(value) {
  return Number(value || 0).toFixed(1);
}

async function fetchWidgetData() {
  const req = new Request(`${API_BASE}/api/widget?user_id=${encodeURIComponent(USER_ID)}`);
  req.method = "GET";
  req.headers = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
  };
  req.timeoutInterval = 15;
  return await req.loadJSON();
}

function buildWidget(data) {
  const w = new ListWidget();
  w.backgroundColor = new Color("#0f172a");
  w.setPadding(12, 12, 12, 12);

  const title = w.addText("NFC Productivity");
  title.font = Font.boldSystemFont(14);
  title.textColor = Color.white();

  const total = w.addText(`Today: ${toHms(data.today_total_seconds)}`);
  total.font = Font.systemFont(12);
  total.textColor = new Color("#e2e8f0");

  const active = data.active_session;
  const modeLine = w.addText(
    active
      ? `Running: ${String(active.mode).toUpperCase()}`
      : "Running: none"
  );
  modeLine.font = Font.mediumSystemFont(12);
  modeLine.textColor = active ? new Color("#22c55e") : new Color("#94a3b8");

  const pie = data.pie || {};
  const pieLine = w.addText(
    `S ${pct(pie.study)}%  C ${pct(pie.coding)}%  F ${pct(pie.fun)}%`
  );
  pieLine.font = Font.systemFont(11);
  pieLine.textColor = new Color("#cbd5e1");

  const streak = w.addText(`Streak: ${Number(data.current_streak || 0)} day(s)`);
  streak.font = Font.systemFont(11);
  streak.textColor = new Color("#cbd5e1");

  // Tap widget to rerun this Scriptable script and force immediate refresh.
  w.url = `scriptable:///run?scriptName=${encodeURIComponent(Script.name())}`;

  // Ask iOS to refresh roughly every 2 minutes.
  w.refreshAfterDate = new Date(Date.now() + REFRESH_MINUTES * 60 * 1000);
  return w;
}

async function main() {
  let data;
  try {
    data = await fetchWidgetData();
  } catch (e) {
    const err = new ListWidget();
    err.backgroundColor = new Color("#7f1d1d");
    const t1 = err.addText("Widget Error");
    t1.textColor = Color.white();
    t1.font = Font.boldSystemFont(13);
    const t2 = err.addText(String(e));
    t2.textColor = new Color("#fee2e2");
    t2.font = Font.systemFont(10);
    err.refreshAfterDate = new Date(Date.now() + 60 * 1000);
    if (config.runsInWidget) {
      Script.setWidget(err);
      Script.complete();
      return;
    }
    await err.presentSmall();
    Script.complete();
    return;
  }

  const widget = buildWidget(data);

  if (config.runsInWidget) {
    Script.setWidget(widget);
  } else {
    await widget.presentSmall();
  }

  Script.complete();
}

await main();
