/**
 * plan-trip-map.js — Location search + Route Planning UI
 * ======================================================
 * UI layer only. Routing algorithm lives in routing/planner.py.
 *
 * - From/To, swap, GPS, map pick
 * - Ranked alternatives (Recommended / Fastest / Cheapest / Fewest transfers)
 * - Detailed legs, transfer warnings
 * - Map: dashed walk legs, solid transit, green board / red drop markers
 */

const CEBU_CENTER = [10.3157, 123.8854];
const CACHE_KEY = "biyahero_last_routes";

const findBtn = document.querySelector("#find-routes-btn");
const swapBtn = document.querySelector("#swap-btn");
const statusEl = document.querySelector("#trip-map-status");
const mapEl = document.querySelector("#trip-map");
const resultsEl = document.querySelector("#results-area");
const validationEl = document.querySelector("#trip-validation-msg");
const sortSelect = document.querySelector("#route-sort");
const maxTransfersEl = document.querySelector("#pref-max-transfers");
const maxWalkEl = document.querySelector("#pref-max-walk");
const passengerEl = document.querySelector("#pref-passenger");
const mapPickBanner = document.querySelector("#map-pick-banner");
const mapPickLabel = document.querySelector("#map-pick-label");
const mapPickConfirm = document.querySelector("#map-pick-confirm");
const mapPickCancel = document.querySelector("#map-pick-cancel");

L.Icon.Default.imagePath = "../api/leaflet/dist/images/";

const map = L.map(mapEl, { zoomControl: true, scrollWheelZoom: true }).setView(CEBU_CENTER, 13);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const routeLayer = L.layerGroup().addTo(map);
const pickLayer = L.layerGroup().addTo(map);

let routePlans = []; // full Route objects from API
let activeRouteId = null;
let pickTarget = null;
let pickLatLng = null;
let lastQuery = null;

function setStatus(msg) {
  if (statusEl) statusEl.textContent = msg;
}
function setValidation(msg) {
  if (!validationEl) return;
  const span = validationEl.querySelector("span") || validationEl;
  span.textContent = msg;
  validationEl.hidden = !msg;
}
function clearValidation() {
  setValidation("");
}

function modeIcon(mode) {
  if (mode === "walk") return "ri-walk-line";
  if (mode === "bus") return "ri-bus-2-line";
  if (mode === "ferry") return "ri-ship-line";
  if (mode === "train") return "ri-train-line";
  return "ri-bus-line";
}

function sortRoutes(list, sortKey) {
  const copy = [...list];
  if (sortKey === "cheapest") {
    copy.sort(
      (a, b) =>
        a.summary.fare_php - b.summary.fare_php ||
        a.summary.duration_min - b.summary.duration_min
    );
  } else if (sortKey === "fewest_transfers") {
    copy.sort(
      (a, b) =>
        a.summary.transfers - b.summary.transfers ||
        a.summary.duration_min - b.summary.duration_min
    );
  } else if (sortKey === "fastest") {
    copy.sort(
      (a, b) =>
        a.summary.duration_min - b.summary.duration_min ||
        a.summary.fare_php - b.summary.fare_php
    );
  } else {
    // recommended
    copy.sort(
      (a, b) =>
        (a.scores?.recommended ?? 99) - (b.scores?.recommended ?? 99) ||
        a.summary.duration_min - b.summary.duration_min
    );
  }
  return copy;
}

function showSkeleton() {
  if (!resultsEl) return;
  resultsEl.innerHTML = `
    <div class="rs-head">
      <div>
        <h2 class="rs-title" id="results-heading">Finding routes…</h2>
        <p class="rs-sub">Usually under a few seconds.</p>
      </div>
    </div>
    <div class="rs-list" aria-busy="true">
      <div class="rs-skeleton"></div>
      <div class="rs-skeleton"></div>
      <div class="rs-skeleton"></div>
    </div>`;
}

function drawRoutePlan(route) {
  routeLayer.clearLayers();
  if (!route?.legs?.length) return;

  const bounds = [];

  route.legs.forEach((leg) => {
    const coords = (leg.geometry?.coordinates || []).map(([lng, lat]) => [lat, lng]);
    if (coords.length >= 2) {
      const isWalk = leg.type === "walk" || leg.geometry?.style === "dashed";
      L.polyline(coords, {
        color: isWalk ? "#524b63" : "#ff7a00",
        weight: isWalk ? 4 : 6,
        opacity: isWalk ? 0.75 : 0.95,
        dashArray: isWalk ? "8 10" : null,
        lineJoin: "round",
        lineCap: "round",
      }).addTo(routeLayer);
      coords.forEach((c) => bounds.push(c));
    }

    if (leg.type === "transit") {
      const board = leg.boarding;
      const drop = leg.dropoff;
      if (board) {
        L.circleMarker([board.lat, board.lng], {
          radius: 9,
          color: "#fff",
          weight: 2,
          fillColor: "#1f7a4c",
          fillOpacity: 1,
        })
          .bindPopup(
            `<strong>Board</strong><br>${board.name}<br><small>${leg.line_code} · ${leg.vehicle_sign || ""}</small>`
          )
          .addTo(routeLayer);
        bounds.push([board.lat, board.lng]);
      }
      if (drop) {
        L.circleMarker([drop.lat, drop.lng], {
          radius: 9,
          color: "#fff",
          weight: 2,
          fillColor: "#b42318",
          fillOpacity: 1,
        })
          .bindPopup(`<strong>Get off</strong><br>${drop.name}`)
          .addTo(routeLayer);
        bounds.push([drop.lat, drop.lng]);
      }
    }
  });

  // Origin / destination endpoints
  const o = route.from;
  const d = route.to;
  L.circleMarker([o.lat, o.lng], {
    radius: 7,
    color: "#fff",
    fillColor: "#0d0c22",
    fillOpacity: 1,
    weight: 2,
  })
    .bindPopup(`<strong>Start</strong><br>${o.name}`)
    .addTo(routeLayer);
  L.circleMarker([d.lat, d.lng], {
    radius: 7,
    color: "#fff",
    fillColor: "#ff7a00",
    fillOpacity: 1,
    weight: 2,
  })
    .bindPopup(`<strong>End</strong><br>${d.name}`)
    .addTo(routeLayer);
  bounds.push([o.lat, o.lng], [d.lat, d.lng]);

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    map.invalidateSize();
  }
  setStatus(`Showing: ${route.summary.mode_chain_text}`);
}

function renderLegDetail(leg) {
  if (leg.type === "walk") {
    const steps = (leg.steps || [])
      .map((s) => `<li>${s.instruction}${s.accessibility ? ` <em>(${s.accessibility})</em>` : ""}</li>`)
      .join("");
    return `
      <div class="rs-leg rs-leg--walk">
        <div class="rs-leg__head"><i class="${modeIcon("walk")}" aria-hidden="true"></i> Walk · ${leg.distance_m} m · ~${leg.duration_min} min</div>
        <p>${leg.from.name} → ${leg.to.name}</p>
        <ol>${steps}</ol>
      </div>`;
  }

  const steps = (leg.steps || []).map((s) => `<li>${s.instruction}</li>`).join("");
  return `
    <div class="rs-leg rs-leg--transit">
      <div class="rs-leg__head">
        <i class="${modeIcon(leg.mode)}" aria-hidden="true"></i>
        ${leg.line_code} · ${leg.line_name || ""} · ~${leg.duration_min} min
      </div>
      <p><span class="rs-dot rs-dot--board"></span> Board: <strong>${leg.boarding.name}</strong>
        ${leg.boarding.landmark ? `(near ${leg.boarding.landmark})` : ""}</p>
      <p class="rs-muted">${leg.vehicle_sign || ""} · ${leg.stops_count} stop(s) · wait ~${leg.expected_wait_min} min</p>
      <p><span class="rs-dot rs-dot--drop"></span> Get off: <strong>${leg.dropoff.name}</strong></p>
      <p class="rs-fare">${leg.fare?.label || "Fare unknown"}</p>
      <ol>${steps}</ol>
    </div>`;
}

function renderResults(suggestions = []) {
  if (!resultsEl) return;

  if (!routePlans.length) {
    resultsEl.innerHTML = `
      <div class="rs-empty" role="status">
        <i class="ri-route-line" aria-hidden="true"></i>
        <h2 id="results-heading">No routes available</h2>
        <p>We could not build a path within your limits.</p>
        <ul>${(suggestions.length ? suggestions : [
          "Increase max walking distance.",
          "Allow more transfers.",
          "Pick a nearby landmark or terminal.",
        ]).map((s) => `<li>${s}</li>`).join("")}</ul>
      </div>`;
    return;
  }

  const sortKey = sortSelect?.value || "recommended";
  const sorted = sortRoutes(routePlans, sortKey);
  if (!activeRouteId || !sorted.find((r) => r.id === activeRouteId)) {
    activeRouteId = sorted.find((r) => r.is_recommended)?.id || sorted[0].id;
  }

  const cards = sorted
    .map((route) => {
      const s = route.summary;
      const active = route.id === activeRouteId ? " is-active" : "";
      const rec = route.is_recommended
        ? `<span class="rs-pill rs-pill--rec">Recommended</span>`
        : `<span class="rs-pill">${s.transfers === 0 ? "Direct" : s.transfers + " transfer(s)"}</span>`;

      const chain = s.mode_chain
        .map(
          (m) =>
            `<span class="rs-chip"><i class="${modeIcon(m.mode)}" aria-hidden="true"></i> ${m.label}</span>`
        )
        .join('<i class="ri-arrow-right-s-line rs-chain-arrow" aria-hidden="true"></i>');

      const xfers = (route.transfers || [])
        .map(
          (t) => `
        <div class="rs-xfer${t.risky ? " is-risky" : ""}">
          <strong>Transfer</strong> — ${t.message}
          ${t.risky ? `<span class="rs-warn">Heads up: ${(t.risk_reasons || []).join(", ")}</span>` : ""}
        </div>`
        )
        .join("");

      const legs =
        route.id === activeRouteId
          ? `<div class="rs-detail" id="route-detail">${route.legs.map(renderLegDetail).join("")}${xfers}
              <button type="button" class="trip-mini-btn" data-save-route="${route.id}">
                <i class="ri-heart-line" aria-hidden="true"></i> Save on this device
              </button>
            </div>`
          : "";

      return `
      <article class="rs-card${active}" data-route-id="${route.id}" tabindex="0" role="button"
        aria-pressed="${route.id === activeRouteId}" aria-label="${s.mode_chain_text}">
        <div class="rs-card__top">
          <div class="rs-chain">${chain}</div>
          ${rec}
        </div>
        <div class="rs-card__meta">
          <span><strong>${s.time_label || `About ${s.duration_min} min`}</strong></span>
          <span><strong>${s.fare_label}</strong></span>
          <span><strong>${s.transfers}</strong> transfer(s)</span>
          <span><strong>~${s.walk_meters} m</strong> walk</span>
        </div>
        <p class="rs-card__times">${s.departure_label} · ${s.arrival_label}</p>
        ${
          s.time_breakdown
            ? `<p class="rs-card__hint">Ride ${s.time_breakdown.riding_min ?? "—"} · Walk ${s.time_breakdown.walking_min ?? "—"} · Wait ${s.time_breakdown.waiting_min ?? "—"} min</p>`
            : `<p class="rs-card__hint">Tap to open steps and update the map.</p>`
        }
        ${legs}
      </article>`;
    })
    .join("");

  resultsEl.innerHTML = `
    <div class="rs-head">
      <div>
        <h2 class="rs-title" id="results-heading">Route options</h2>
        <p class="rs-sub">Estimates only — dashed lines are walking; orange lines are rides. Green = board, red = get off.</p>
      </div>
      <label class="rs-sort">
        <span>Sort</span>
        <select id="route-sort-inner" aria-label="Sort routes">
          <option value="recommended"${sortKey === "recommended" ? " selected" : ""}>Recommended</option>
          <option value="fastest"${sortKey === "fastest" ? " selected" : ""}>Fastest</option>
          <option value="fewest_transfers"${sortKey === "fewest_transfers" ? " selected" : ""}>Fewest transfers</option>
          <option value="cheapest"${sortKey === "cheapest" ? " selected" : ""}>Cheapest</option>
        </select>
      </label>
    </div>
    <div class="rs-list">${cards}</div>
    <p class="rs-foot">Wrong info? <a href="report.html">Report Issue</a></p>`;

  resultsEl.querySelectorAll(".rs-card").forEach((card) => {
    const activate = () => {
      activeRouteId = card.getAttribute("data-route-id");
      const route = routePlans.find((r) => r.id === activeRouteId);
      renderResults(suggestions);
      if (route) drawRoutePlan(route);
    };
    card.addEventListener("click", (e) => {
      if (e.target.closest("[data-save-route]")) return;
      activate();
    });
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        activate();
      }
    });
  });

  resultsEl.querySelector("#route-sort-inner")?.addEventListener("change", (e) => {
    if (sortSelect) sortSelect.value = e.target.value;
    renderResults(suggestions);
    const route = routePlans.find((r) => r.id === activeRouteId);
    if (route) drawRoutePlan(route);
  });

  resultsEl.querySelectorAll("[data-save-route]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const id = btn.getAttribute("data-save-route");
      const route = routePlans.find((r) => r.id === id);
      if (!route) return;
      // Guests can keep a trip on this device — no account needed
      const saved = {
        route,
        query: lastQuery,
        saved_at: new Date().toISOString(),
      };
      try {
        const key = "biyahero_saved_routes";
        const list = JSON.parse(localStorage.getItem(key) || "[]");
        list.unshift(saved);
        localStorage.setItem(key, JSON.stringify(list.slice(0, 20)));
        setStatus(`Saved on this device: ${route.summary.mode_chain_text}`);
        btn.innerHTML = '<i class="ri-heart-fill" aria-hidden="true"></i> Saved here';
      } catch (_) {
        setValidation("Could not save on this device. Try again.");
      }
    });
  });
}

function clearResults() {
  routePlans = [];
  activeRouteId = null;
  if (resultsEl) resultsEl.innerHTML = "";
}

function validate() {
  const pickers = window.LocationPickers;
  if (!pickers) return false;
  const startPicker = pickers["start-picker"];
  const destPicker = pickers["dest-picker"];
  const start = startPicker?.getSelected();
  const dest = destPicker?.getSelected();
  let valid = true;
  if (!start) {
    startPicker?.setError("Please choose a starting place.");
    valid = false;
  } else startPicker?.clearError();
  if (!dest) {
    destPicker?.setError("Please choose a destination.");
    valid = false;
  } else destPicker?.clearError();
  if (!valid) {
    setValidation("Please fill both From and To before searching.");
    return false;
  }
  if (start.name === dest.name && start.lat === dest.lat && start.lng === dest.lng) {
    setValidation("Start and end cannot be the same.");
    return false;
  }
  clearValidation();
  return true;
}

async function showRoute() {
  if (!validate()) return;
  const start = window.LocationPickers["start-picker"].getSelected();
  const dest = window.LocationPickers["dest-picker"].getSelected();

  clearResults();
  routeLayer.clearLayers();
  showSkeleton();
  findBtn.disabled = true;
  findBtn.classList.add("is-loading");
  findBtn.innerHTML = '<i class="ri-loader-4-line" aria-hidden="true"></i> Finding…';
  setStatus(`Planning routes from ${start.name} to ${dest.name}…`);

  const body = {
    from: start,
    to: dest,
    max_transfers: Number(maxTransfersEl?.value || 3),
    max_walk_m: Number(maxWalkEl?.value || 1800),
    passenger: passengerEl?.value || "regular",
  };
  lastQuery = body;

  try {
    const res = await fetch("/api/routes/search", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok || !data.ok) {
      setValidation(data.error || "Could not plan routes. Try again.");
      routePlans = [];
      renderResults(data.suggestions || []);
      return;
    }

    routePlans = data.routes || [];
    activeRouteId = routePlans.find((r) => r.is_recommended)?.id || routePlans[0]?.id || null;
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ query: body, routes: routePlans, at: Date.now() }));
    } catch (_) { /* ignore quota */ }

    renderResults(data.suggestions || []);
    const active = routePlans.find((r) => r.id === activeRouteId);
    if (active) drawRoutePlan(active);
    else setStatus("No routes available for that pair.");
  } catch (_) {
    setValidation("No internet right now. Trying last saved results…");
    try {
      const cached = JSON.parse(localStorage.getItem(CACHE_KEY) || "null");
      if (cached?.routes?.length) {
        routePlans = cached.routes;
        activeRouteId = routePlans[0].id;
        renderResults(["Showing a previously viewed plan (offline)."]);
        drawRoutePlan(routePlans[0]);
      } else {
        routePlans = [];
        renderResults();
      }
    } catch (__) {
      routePlans = [];
      renderResults();
    }
  } finally {
    findBtn.disabled = false;
    findBtn.classList.remove("is-loading");
    findBtn.innerHTML = '<i class="ri-search-line" aria-hidden="true"></i> Find Routes';
  }
}

function swapLocations() {
  const pickers = window.LocationPickers;
  if (!pickers) return;
  const startPicker = pickers["start-picker"];
  const destPicker = pickers["dest-picker"];
  if (!startPicker || !destPicker) return;
  const startLoc = startPicker.getSelected();
  const destLoc = destPicker.getSelected();
  if (destLoc) startPicker.setValue(destLoc);
  else startPicker.clear();
  if (startLoc) destPicker.setValue(startLoc);
  else destPicker.clear();
  clearValidation();
  clearResults();
  routeLayer.clearLayers();
  setStatus("Places swapped. Tap Find Routes to search again.");
  swapBtn?.classList.add("swap-btn--spinning");
  setTimeout(() => swapBtn?.classList.remove("swap-btn--spinning"), 400);
}

async function useCurrentLocation(pickerId) {
  const picker = window.LocationPickers?.[pickerId];
  if (!picker) return;
  if (!navigator.geolocation) {
    setValidation("This browser cannot read your location. Type a place or pick on the map.");
    return;
  }
  setStatus("Getting your location…");
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      const place = await window.LocationSearch.reverseGeocode(lat, lng);
      const loc = place || {
        name: "My current location",
        type: "current",
        city: "Cebu",
        barangay: "Near you",
        lat,
        lng,
      };
      loc.lat = lat;
      loc.lng = lng;
      picker.setValue(loc);
      map.setView([lat, lng], 15);
      setStatus(`Using your location: ${loc.name}`);
    },
    (err) => {
      if (err.code === err.PERMISSION_DENIED) {
        setValidation("Location permission is off. Type a place or pick on the map.");
      } else if (err.code === err.POSITION_UNAVAILABLE) {
        setValidation("GPS looks off. Turn on location services, or pick on the map.");
      } else {
        setValidation("Could not get your location. Try again or pick on the map.");
      }
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
  );
}

function startMapPick(pickerId) {
  pickTarget = pickerId;
  pickLatLng = null;
  pickLayer.clearLayers();
  mapPickBanner.hidden = false;
  mapPickLabel.textContent = "Tap the map to drop a pin.";
  mapPickConfirm.disabled = true;
  mapEl.classList.add("trip-map--picking");
  setStatus("Map pick mode: tap the map, then Confirm.");
}

function cancelMapPick() {
  pickTarget = null;
  pickLatLng = null;
  pickLayer.clearLayers();
  mapPickBanner.hidden = true;
  mapEl.classList.remove("trip-map--picking");
  setStatus("Select From and To, then tap Find Routes.");
}

async function confirmMapPick() {
  if (!pickTarget || !pickLatLng) return;
  const picker = window.LocationPickers?.[pickTarget];
  if (!picker) return;
  mapPickConfirm.disabled = true;
  mapPickLabel.textContent = "Getting the address…";
  const place = await window.LocationSearch.reverseGeocode(pickLatLng.lat, pickLatLng.lng);
  const loc = place || {
    name: `Map pin (${pickLatLng.lat.toFixed(4)}, ${pickLatLng.lng.toFixed(4)})`,
    type: "map",
    city: "Cebu",
    barangay: "Selected point",
    lat: pickLatLng.lat,
    lng: pickLatLng.lng,
  };
  loc.lat = pickLatLng.lat;
  loc.lng = pickLatLng.lng;
  loc.type = "map";
  picker.setValue(loc);
  cancelMapPick();
  setStatus(`Map place set: ${loc.name}`);
}

map.on("click", (e) => {
  if (!pickTarget) return;
  pickLatLng = e.latlng;
  pickLayer.clearLayers();
  L.marker(e.latlng).addTo(pickLayer);
  mapPickLabel.textContent = `Pin at ${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}. Tap again to move.`;
  mapPickConfirm.disabled = false;
});

findBtn?.addEventListener("click", showRoute);
swapBtn?.addEventListener("click", swapLocations);
mapPickConfirm?.addEventListener("click", confirmMapPick);
mapPickCancel?.addEventListener("click", cancelMapPick);
sortSelect?.addEventListener("change", () => {
  if (!routePlans.length) return;
  renderResults();
  const route = routePlans.find((r) => r.id === activeRouteId);
  if (route) drawRoutePlan(route);
});

document.querySelectorAll("[data-use-location]").forEach((btn) => {
  btn.addEventListener("click", () => useCurrentLocation(btn.getAttribute("data-use-location")));
});
document.querySelectorAll("[data-map-pick]").forEach((btn) => {
  btn.addEventListener("click", () => startMapPick(btn.getAttribute("data-map-pick")));
});

document.addEventListener("location-selected", () => clearValidation());
document.addEventListener("location-cleared", () => {
  clearResults();
  routeLayer.clearLayers();
  setStatus("Select From and To, then tap Find Routes.");
});

window.addEventListener("load", () => {
  map.invalidateSize();
  setStatus("Select From and To, then tap Find Routes.");

  // Ensure Recommended is default sort
  if (sortSelect && ![...sortSelect.options].some((o) => o.value === "recommended")) {
    const opt = document.createElement("option");
    opt.value = "recommended";
    opt.textContent = "Recommended";
    sortSelect.insertBefore(opt, sortSelect.firstChild);
  }
  if (sortSelect) sortSelect.value = "recommended";

  const params = new URLSearchParams(window.location.search);
  const fromQ = params.get("from");
  const toQ = params.get("to");
  (async () => {
    if (fromQ && window.LocationSearch) {
      const { results } = await window.LocationSearch.searchLocations(fromQ);
      const hit = results.find((r) => r.name.toLowerCase().includes(fromQ.toLowerCase())) || results[0];
      if (hit) window.LocationPickers["start-picker"]?.setValue(hit);
    }
    if (toQ && window.LocationSearch) {
      const { results } = await window.LocationSearch.searchLocations(toQ);
      const hit = results.find((r) => r.name.toLowerCase().includes(toQ.toLowerCase())) || results[0];
      if (hit) window.LocationPickers["dest-picker"]?.setValue(hit);
    }
    if (params.get("save") === "1") {
      setValidation("Log in to save a route. Your last search places were kept when possible.");
    }
  })();
});
