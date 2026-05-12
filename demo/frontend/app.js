/* global DEMO_API_BASE */

(function () {
  const PUBLIC_EVENT_ID = "DEMO-EVT-PUBLIC-001";
  const PRIVATE_EVENT_ID = "DEMO-EVT-PRIVATE-001";

  const apiInput = document.getElementById("apiBase");
  const saveBtn = document.getElementById("saveApiBase");
  const reloadBtn = document.getElementById("reloadData");
  const statusLine = document.getElementById("statusLine");
  const visibilityChecks = document.getElementById("visibilityChecks");
  const mapEventList = document.getElementById("mapEventList");
  const governanceSignals = document.getElementById("governanceSignals");
  const healthLink = document.getElementById("healthLink");
  const mapEventsLink = document.getElementById("mapEventsLink");

  const stored = localStorage.getItem("demo_api_base");
  const fallback = (typeof DEMO_API_BASE === "string" && DEMO_API_BASE) || "http://localhost:8010";
  let apiBase = (stored || fallback).replace(/\/$/, "");
  apiInput.value = apiBase;

  function setStatus(text) {
    statusLine.textContent = text;
  }

  function setLinks() {
    healthLink.href = `${apiBase}/health`;
    mapEventsLink.href = `${apiBase}/api/map/events`;
  }

  function addCheck(target, text, klass) {
    const li = document.createElement("li");
    li.className = klass;
    li.textContent = text;
    target.appendChild(li);
  }

  async function getJson(path) {
    const res = await fetch(`${apiBase}${path}`);
    if (!res.ok) {
      throw new Error(`${path} returned ${res.status}`);
    }
    return res.json();
  }

  function clearLists() {
    visibilityChecks.innerHTML = "";
    mapEventList.innerHTML = "";
    governanceSignals.innerHTML = "";
  }

  async function loadDemo() {
    clearLists();
    setStatus("Loading demo data from backend...");
    try {
      const health = await getJson("/health");
      addCheck(governanceSignals, `Backend health: ${health.status || "unknown"}`, "ok");

      const mapPayload = await getJson("/api/map/events");
      const ids = (mapPayload.features || [])
        .map((feature) => feature && feature.properties && feature.properties.event_id)
        .filter(Boolean);

      ids.forEach((id) => {
        const li = document.createElement("li");
        li.textContent = id;
        mapEventList.appendChild(li);
      });

      if (ids.includes(PUBLIC_EVENT_ID)) {
        addCheck(visibilityChecks, `${PUBLIC_EVENT_ID} is visible (expected).`, "ok");
      } else {
        addCheck(visibilityChecks, `${PUBLIC_EVENT_ID} missing from map events (unexpected).`, "bad");
      }

      if (!ids.includes(PRIVATE_EVENT_ID)) {
        addCheck(visibilityChecks, `${PRIVATE_EVENT_ID} is hidden (expected).`, "ok");
      } else {
        addCheck(visibilityChecks, `${PRIVATE_EVENT_ID} leaked into map events (unexpected).`, "bad");
      }

      addCheck(
        governanceSignals,
        `Returned map features: ${Array.isArray(mapPayload.features) ? mapPayload.features.length : 0}`,
        "ok"
      );
      addCheck(
        governanceSignals,
        "Public visibility is review-gated by runtime endpoints.",
        "ok"
      );
      addCheck(
        governanceSignals,
        "Demo data is synthetic fixture-only; no live scraping.",
        "ok"
      );
      setStatus("Demo data loaded.");
    } catch (err) {
      addCheck(visibilityChecks, `Error: ${err.message}`, "bad");
      setStatus("Failed to load demo data. Check backend and API base.");
    }
  }

  saveBtn.addEventListener("click", () => {
    apiBase = apiInput.value.trim().replace(/\/$/, "");
    if (!apiBase) {
      setStatus("API base cannot be empty.");
      return;
    }
    localStorage.setItem("demo_api_base", apiBase);
    setLinks();
    setStatus(`Saved API base: ${apiBase}`);
  });

  reloadBtn.addEventListener("click", loadDemo);

  setLinks();
  loadDemo();
})();
