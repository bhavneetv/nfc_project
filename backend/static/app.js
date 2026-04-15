const statusEl = document.getElementById("status");
const userInput = document.getElementById("userId");
const enableNotificationsBtn = document.getElementById("enableNotificationsBtn");

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

function isStandalonePwa() {
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
}

async function enableNotifications() {
  try {
    if (!isStandalonePwa()) {
      setStatus("Open this app from Home Screen first, then tap Enable Notifications.");
      return;
    }
    if (!("Notification" in window)) {
      setStatus("Notifications are not supported in this browser.");
      return;
    }

    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      setStatus("Notification permission denied.");
      return;
    }

    await subscribePush();
    if (enableNotificationsBtn) enableNotificationsBtn.style.display = "none";
    setStatus("Notifications enabled.");
  } catch (err) {
    setStatus(`Notification setup error: ${err.message}`);
  }
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

function viewLogs() {
  const userId = getUserId();
  window.location.href = `/logs.html?user_id=${encodeURIComponent(userId)}`;
}

window.startMode = startMode;
window.stopMode = stopMode;
window.enableNotifications = enableNotifications;
window.viewLogs = viewLogs;

(async () => {
  try {
    await loadConfig();

    if ("Notification" in window && Notification.permission === "granted") {
      await subscribePush();
      if (enableNotificationsBtn) enableNotificationsBtn.style.display = "none";
      setStatus("Ready (notifications enabled)");
      return;
    }

    if (enableNotificationsBtn) enableNotificationsBtn.style.display = "block";
    setStatus("Tap Enable Notifications to allow push.");
  } catch (err) {
    setStatus(`Init error: ${err.message}`);
  }
})();
