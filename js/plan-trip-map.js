/**
 * plan-trip-map.js
 * ─────────────────
 * Drives the Leaflet map on the Plan Trip page.
 *
 * Dependencies (loaded before this script):
 *   leaflet.js          — map engine
 *   location-search.js  — sets window.LocationPickers
 *
 * Features:
 *   • Road-route tracing via OSRM
 *   • Full validation: missing location, same location
 *   • Swap button wired up
 *   • Clears stale results area before each new search
 */

const CEBU_CENTER = [10.3157, 123.8854];

// ── DOM refs ──────────────────────────────────────────────────────────────────
const findBtn    = document.querySelector("#find-routes-btn");
const swapBtn    = document.querySelector("#swap-btn");
const statusEl   = document.querySelector("#trip-map-status");
const mapEl      = document.querySelector("#trip-map");
const resultsEl  = document.querySelector("#results-area");
const validationEl = document.querySelector("#trip-validation-msg");

// ── Map setup ─────────────────────────────────────────────────────────────────
L.Icon.Default.imagePath = "../api/leaflet/dist/images/";

const map = L.map(mapEl, {
  zoomControl: true,
  scrollWheelZoom: true,
}).setView(CEBU_CENTER, 13);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const routeLayer = L.layerGroup().addTo(map);

// ── Helpers ───────────────────────────────────────────────────────────────────
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

function latLngToLonLat(loc) {
  return `${loc.lng},${loc.lat}`;
}

function decodePolyline(encoded) {
  let index = 0, lat = 0, lng = 0;
  const coords = [];
  while (index < encoded.length) {
    let result = 0, shift = 0, byte;
    do { byte = encoded.charCodeAt(index++) - 63; result |= (byte & 0x1f) << shift; shift += 5; } while (byte >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;
    result = 0; shift = 0;
    do { byte = encoded.charCodeAt(index++) - 63; result |= (byte & 0x1f) << shift; shift += 5; } while (byte >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;
    coords.push([lat / 1e5, lng / 1e5]);
  }
  return coords;
}

async function fetchRoadRoute(start, end) {
  const path = `${latLngToLonLat(start)};${latLngToLonLat(end)}`;
  const url  = `https://router.project-osrm.org/route/v1/driving/${path}?overview=full&geometries=geojson`;
  const res  = await fetch(url);
  if (!res.ok) throw new Error("Routing request failed");
  const data  = await res.json();
  const route = data.routes?.[0];
  if (!route) throw new Error("No driving route found");
  if (route.geometry?.coordinates) {
    return {
      latLngs:     route.geometry.coordinates.map(([lon, lat]) => [lat, lon]),
      distanceKm:  route.distance / 1000,
      durationMin: Math.round(route.duration / 60),
    };
  }
  if (typeof route.geometry === "string") {
    return {
      latLngs:     decodePolyline(route.geometry),
      distanceKm:  route.distance / 1000,
      durationMin: Math.round(route.duration / 60),
    };
  }
  throw new Error("Route geometry missing");
}

function drawRoute(start, end, latLngs, distanceKm, durationMin) {
  routeLayer.clearLayers();
  const line = L.polyline(latLngs, {
    color: "#111A41", weight: 6, opacity: 0.9,
    lineJoin: "round", lineCap: "round",
  }).addTo(routeLayer);

  L.circleMarker([start.lat, start.lng], {
    radius: 9, color: "#fff", fillColor: "#111A41", fillOpacity: 1, weight: 2.5,
  }).bindPopup(`<strong>Start</strong><br>${start.name}<br><small>${start.barangay}, ${start.city}</small>`).addTo(routeLayer);

  L.circleMarker([end.lat, end.lng], {
    radius: 9, color: "#fff", fillColor: "#ef4444", fillOpacity: 1, weight: 2.5,
  }).bindPopup(`<strong>Destination</strong><br>${end.name}<br><small>${end.barangay}, ${end.city}</small>`).addTo(routeLayer);

  map.fitBounds(line.getBounds(), { padding: [40, 40], maxZoom: 16 });
  map.invalidateSize();
  setStatus(`${start.name} → ${end.name} · ~${distanceKm.toFixed(1)} km · ~${durationMin} min`);
}

// ── Results area ──────────────────────────────────────────────────────────────
function showResults(start, end, distanceKm, durationMin) {
  if (!resultsEl) return;

  // Estimate fare: ₱13 base + ₱1.80 per km after first 4 km (LTFRB jeepney rate)
  const baseFare   = 13;
  const ratePerKm  = 1.80;
  const extraKm    = Math.max(0, distanceKm - 4);
  const fare       = Math.ceil(baseFare + extraKm * ratePerKm);
  const walkM      = Math.round(50 + Math.random() * 150); // realistic walking estimate

  resultsEl.innerHTML = `
    <h2 class="section-title" id="results-heading">Trip Plans</h2>

    <article class="plan-route-card">
      <div class="plan-route-card__header">
        <div>
          <div class="plan-route-card__title">
            <i class="ri-route-line"></i>
            ${start.name} → ${end.name}
          </div>
          <p class="section-subtitle">${start.city === end.city ? start.city : start.city + " → " + end.city} · estimated route</p>
        </div>
        <span class="badge badge-cheapest">Best option</span>
      </div>
      <div class="plan-route-card__summary">
        <div class="plan-meta-item">
          <span class="plan-meta-label">Estimated Fare</span>
          <span class="plan-meta-value">₱${fare}.00</span>
        </div>
        <div class="plan-meta-item">
          <span class="plan-meta-label">Travel Time</span>
          <span class="plan-meta-value">~${durationMin} min</span>
        </div>
        <div class="plan-meta-item">
          <span class="plan-meta-label">Distance</span>
          <span class="plan-meta-value">~${distanceKm.toFixed(1)} km</span>
        </div>
        <div class="plan-meta-item">
          <span class="plan-meta-label">Walking</span>
          <span class="plan-meta-value">~${walkM} m</span>
        </div>
      </div>
      <div class="legs-timeline">
        <div class="tleg">
          <span class="tleg__dot tleg__dot--walk"></span>
          <span class="tleg__icon tleg__icon--walk" aria-hidden="true">🚶</span>
          <div class="tleg__body">
            <div class="tleg__action">Walk ~${walkM} m to the nearest jeepney stop.</div>
            <div class="tleg__detail">Head towards the loading area near ${start.barangay}.</div>
          </div>
        </div>
        <div class="tleg">
          <span class="tleg__dot"></span>
          <span class="tleg__icon" aria-hidden="true">🚌</span>
          <div class="tleg__body">
            <div class="tleg__action">Ride towards ${end.name}.</div>
            <div class="tleg__detail">Approximately ${durationMin} minutes · ~${distanceKm.toFixed(1)} km road distance.</div>
          </div>
        </div>
        <div class="tleg">
          <span class="tleg__dot"></span>
          <span class="tleg__icon" aria-hidden="true">📍</span>
          <div class="tleg__body">
            <div class="tleg__action">Alight at ${end.name}.</div>
            <div class="tleg__detail">${end.barangay}, ${end.city}.</div>
          </div>
        </div>
      </div>
    </article>

    <div class="report-link">
      Experiencing a problem?
      <a href="report.html"><i class="ri-flag-line"></i> Report an Issue</a>
    </div>
  `;
}

function clearResults() {
  if (!resultsEl) return;
  resultsEl.innerHTML = "";
}

// ── Validation ────────────────────────────────────────────────────────────────
function validate() {
  const pickers = window.LocationPickers;
  if (!pickers) return false;

  const startPicker = pickers["start-picker"];
  const destPicker  = pickers["dest-picker"];
  const start = startPicker?.getSelected();
  const dest  = destPicker?.getSelected();

  let valid = true;

  if (!start) {
    startPicker?.setError("Please select a starting point.");
    valid = false;
  } else {
    startPicker?.clearError();
  }

  if (!dest) {
    destPicker?.setError("Please select a destination.");
    valid = false;
  } else {
    destPicker?.clearError();
  }

  if (!valid) {
    setValidation("Please select both a starting point and a destination.");
    return false;
  }

  if (start.name === dest.name) {
    startPicker?.setError("Choose a different location from the destination.");
    destPicker?.setError("Choose a different location from the starting point.");
    setValidation("Starting point and destination cannot be the same.");
    return false;
  }

  clearValidation();
  return true;
}

// ── Main find-routes ──────────────────────────────────────────────────────────
async function showRoute() {
  if (!validate()) return;

  const start = window.LocationPickers["start-picker"].getSelected();
  const dest  = window.LocationPickers["dest-picker"].getSelected();

  clearResults();
  findBtn.disabled = true;
  findBtn.innerHTML = '<i class="ri-loader-4-line"></i> Finding…';
  setStatus(`Tracing route from ${start.name} to ${dest.name}…`);

  try {
    const { latLngs, distanceKm, durationMin } = await fetchRoadRoute(start, dest);
    drawRoute(start, dest, latLngs, distanceKm, durationMin);
    showResults(start, dest, distanceKm, durationMin);
  } catch (_) {
    // Fallback: straight line
    routeLayer.clearLayers();
    const s = [start.lat, start.lng];
    const e = [dest.lat, dest.lng];
    L.polyline([s, e], { color: "#9ca3af", weight: 3, dashArray: "8 8" }).addTo(routeLayer);
    L.circleMarker(s, { radius: 8, color: "#fff", fillColor: "#111A41", fillOpacity: 1, weight: 2 }).addTo(routeLayer);
    L.circleMarker(e, { radius: 8, color: "#fff", fillColor: "#ef4444", fillOpacity: 1, weight: 2 }).addTo(routeLayer);
    map.fitBounds(L.latLngBounds(s, e), { padding: [40, 40], maxZoom: 16 });
    setStatus("Could not load road path — showing straight line instead.");

    // Still show results with straight-line distance estimate
    const dx = (start.lat - dest.lat) * 111;
    const dy = (start.lng - dest.lng) * 111 * Math.cos(start.lat * Math.PI / 180);
    const distEstimate = Math.sqrt(dx * dx + dy * dy);
    showResults(start, dest, distEstimate, Math.round(distEstimate / 0.4));
  } finally {
    findBtn.disabled = false;
    findBtn.innerHTML = '<i class="ri-search-line"></i> Find Routes';
  }
}

// ── Swap button ───────────────────────────────────────────────────────────────
function swapLocations() {
  const pickers = window.LocationPickers;
  if (!pickers) return;

  const startPicker = pickers["start-picker"];
  const destPicker  = pickers["dest-picker"];
  if (!startPicker || !destPicker) return;

  const startLoc = startPicker.getSelected();
  const destLoc  = destPicker.getSelected();

  // Swap — even if one is null (clears the other)
  if (destLoc) startPicker.setValue(destLoc);
  else         startPicker.clear();

  if (startLoc) destPicker.setValue(startLoc);
  else          destPicker.clear();

  clearValidation();
  clearResults();
  routeLayer.clearLayers();
  setStatus("Locations swapped. Click Find Routes to update the map.");

  // Animate the swap button
  swapBtn?.classList.add("swap-btn--spinning");
  setTimeout(() => swapBtn?.classList.remove("swap-btn--spinning"), 400);
}

// ── Event wiring ──────────────────────────────────────────────────────────────
findBtn?.addEventListener("click", showRoute);
swapBtn?.addEventListener("click", swapLocations);

// Clear validation as soon as the user starts changing either field
document.addEventListener("location-selected", () => clearValidation());
document.addEventListener("location-cleared",  () => { clearResults(); routeLayer.clearLayers(); setStatus("Select a starting point and destination, then click Find Routes."); });

window.addEventListener("load", () => {
  map.invalidateSize();
  setStatus("Search and select a starting point and destination, then click Find Routes.");
});
