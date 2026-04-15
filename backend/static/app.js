const statusEl = document.getElementById("status");
const userInput = document.getElementById("userId");

let config = { vapidPublicKey: "", defaultUserId: "demo-user" };
const params = new URLSearchParams(window.location.search);

function setStatus(text) {
  if (statusEl) statusEl.textContent = text;
}

function getUserId() {
  const fromInput = userInput?.value?.trim();
  if (fromInput) {
    localStorage.setItem("nfc_user_id", fromInput);
    return fromInput;
  }
  const fromStorage = localStorage.getItem("nfc_user_id");
  if (fromStorage) return fromStorage;
  return config.defaultUserId || "demo-user";
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
}

async function subscribePush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return;
  if (!config.vapidPublicKey) return;

  const registration = await navigator.serviceWorker.register("/sw.js");
  const existing = await registration.pushManager.getSubscription();
  const sub = existing || await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(config.vapidPublicKey),
  });

  const subJson = sub.toJSON();
  await fetch("/api/push/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: getUserId(),
      endpoint: subJson.endpoint,
      keys: subJson.keys,
    }),
  });
}

async function loadConfig() {
  const res = await fetch("/api/config");
  config = await res.json();
  const queryUser = params.get("user_id");
  if (queryUser) localStorage.setItem("nfc_user_id", queryUser);
  const savedUser = queryUser || localStorage.getItem("nfc_user_id") || config.defaultUserId;
  if (userInput) userInput.value = savedUser;
}

async function startMode(mode) {
  setStatus("Starting session...");
  try {
    const res = await fetch("/api/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: getUserId(),
        mode,
        device_status: "pc_on",
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed");
    setStatus(`Started ${data.session.mode} at ${new Date(data.session.start_time).toLocaleTimeString()}`);
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
}

async function stopMode() {
  setStatus("Stopping session...");
  try {
    const res = await fetch("/api/session/stop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: getUserId(),
        device_status: "pc_on",
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed");
    const mins = Math.max(1, Math.floor((data.session.duration_seconds || 0) / 60));
    setStatus(`Stopped. Duration ${mins} min.`);
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
}

window.startMode = startMode;
window.stopMode = stopMode;

(async () => {
  try {
    await loadConfig();
    await subscribePush();
    setStatus("Ready");
  } catch (err) {
    setStatus(`Init error: ${err.message}`);
  }
})();
