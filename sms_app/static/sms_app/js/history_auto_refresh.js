(function () {
  const root = document.getElementById("history-auto-refresh");
  if (!root) {
    return;
  }

  const endpoint = root.dataset.endpoint;
  const limit = root.dataset.limit || "25";
  const empty = root.dataset.empty || "";
  if (!endpoint) {
    return;
  }

  const intervalMs = 3000;
  const maxTicks = 40; // ~2 minutes
  let ticks = 0;
  let timer = null;
  let inFlight = false;

  function hasQueued() {
    return Boolean(root.querySelector(".status-queued"));
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  async function refreshOnce() {
    if (inFlight) {
      return;
    }
    inFlight = true;
    try {
      const url = new URL(endpoint, window.location.origin);
      url.searchParams.set("limit", limit);
      if (empty) {
        url.searchParams.set("empty", empty);
      }
      const response = await fetch(url.toString(), {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      if (typeof data.html === "string") {
        root.innerHTML = data.html;
      }
      ticks += 1;
      if (!data.queued_count || ticks >= maxTicks) {
        stop();
      }
    } catch (err) {
      // Keep UI usable if refresh fails.
    } finally {
      inFlight = false;
    }
  }

  function start() {
    if (!hasQueued()) {
      return;
    }
    stop();
    ticks = 0;
    timer = setInterval(refreshOnce, intervalMs);
    // First poll a bit sooner after send/redirect.
    setTimeout(refreshOnce, 1200);
  }

  start();
})();
