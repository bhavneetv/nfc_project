self.addEventListener("push", (event) => {
  if (!event.data) return;
  const payload = event.data.json();

  event.waitUntil(
    self.registration.showNotification(payload.title || "NFC Tracker", {
      body: payload.body || "You have an update",
      data: payload.url || "/select.html",
      badge: "/static/badge.png",
      icon: "/static/icon.png",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = event.notification.data || "/select.html";
  event.waitUntil(clients.openWindow(target));
});
