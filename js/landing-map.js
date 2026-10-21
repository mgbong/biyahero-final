const CEBU_CENTER = [10.3157, 123.8854];

const PLACE_COORDS = {
  Colon: [10.2978, 123.8988],
  Carbon: [10.2927, 123.9028],
  "Fuente Osmeña": [10.3097, 123.8933],
  Parkmall: [10.3269, 123.9348],
  "Mactan Airport": [10.3074, 123.9794],
  "SM City Cebu": [10.3116, 123.9184],
  "IT Park": [10.3275, 123.9055],
  "Ayala Center Cebu": [10.3174, 123.9054],
};

const startSelect = document.querySelector("#starting-point");
const destSelect = document.querySelector("#destination");
const findBtn = document.querySelector("#find-routes-btn");
const statusEl = document.querySelector("#trip-map-status");
const mapEl = document.querySelector("#landing-map");
const mapPane = document.querySelector("#landing-map-pane");
const fullscreenBtn = document.querySelector("#map-fullscreen-btn");
const formEl = document.querySelector("#landing-directions");

let map;
let routeLayer;
let mapReady = false;

function setStatus(message) {
  if (statusEl) {
    statusEl.textContent = message;
  }
}

function latLngToLonLat(latLng) {
  return `${latLng[1]},${latLng[0]}`;
}

async function fetchRoadRoute(start, end) {
  const path = `${latLngToLonLat(start)};${latLngToLonLat(end)}`;
  const url = `https://router.project-osrm.org/route/v1/driving/${path}?overview=full&geometries=geojson`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Routing request failed");
  }

  const data = await response.json();
  const route = data.routes && data.routes[0];

  if (!route || !route.geometry || !route.geometry.coordinates) {
    throw new Error("No driving route found");
  }

  return {
    latLngs: route.geometry.coordinates.map(([lon, lat]) => [lat, lon]),
    distanceKm: route.distance / 1000,
    durationMin: Math.round(route.duration / 60),
  };
}

function initMap() {
  if (mapReady || !mapEl || typeof L === "undefined") {
    return;
  }

  L.Icon.Default.imagePath = "api/leaflet/dist/images/";

  map = L.map(mapEl, {
    zoomControl: false,
    scrollWheelZoom: true,
  }).setView(CEBU_CENTER, 13);

  L.control.zoom({ position: "topright" }).addTo(map);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  routeLayer = L.layerGroup().addTo(map);
  mapReady = true;
  map.invalidateSize();
}

function drawRoute(startName, destName, start, end, latLngs, distanceKm, durationMin) {
  routeLayer.clearLayers();

  const line = L.polyline(latLngs, {
    color: "#111A41",
    weight: 6,
    opacity: 0.92,
    lineJoin: "round",
    lineCap: "round",
  }).addTo(routeLayer);

  L.circleMarker(start, {
    radius: 9,
    color: "#ffffff",
    fillColor: "#111A41",
    fillOpacity: 1,
    weight: 3,
  })
    .bindPopup(`<strong>Start</strong><br>${startName}`)
    .addTo(routeLayer);

  L.circleMarker(end, {
    radius: 9,
    color: "#ffffff",
    fillColor: "#ef4444",
    fillOpacity: 1,
    weight: 3,
  })
    .bindPopup(`<strong>Destination</strong><br>${destName}`)
    .addTo(routeLayer);

  map.fitBounds(line.getBounds(), { padding: [48, 48], maxZoom: 15 });
  map.invalidateSize();

  setStatus(`${startName} → ${destName} · ~${distanceKm.toFixed(1)} km · ~${durationMin} min`);
}

async function showRoute() {
  if (!mapReady) {
    initMap();
  }

  const startName = startSelect.value;
  const destName = destSelect.value;
  const start = PLACE_COORDS[startName];
  const end = PLACE_COORDS[destName];

  if (!start || !end) {
    setStatus("Choose a starting point and destination.");
    return;
  }

  findBtn.disabled = true;
  setStatus(`Tracing the road from ${startName} to ${destName}…`);

  try {
    const { latLngs, distanceKm, durationMin } = await fetchRoadRoute(start, end);
    drawRoute(startName, destName, start, end, latLngs, distanceKm, durationMin);
  } catch (error) {
    routeLayer.clearLayers();
    L.polyline([start, end], {
      color: "#9ca3af",
      weight: 3,
      dashArray: "8 8",
    }).addTo(routeLayer);
    L.circleMarker(start, {
      radius: 9,
      color: "#ffffff",
      fillColor: "#111A41",
      fillOpacity: 1,
      weight: 3,
    }).addTo(routeLayer);
    L.circleMarker(end, {
      radius: 9,
      color: "#ffffff",
      fillColor: "#ef4444",
      fillOpacity: 1,
      weight: 3,
    }).addTo(routeLayer);
    map.fitBounds(L.latLngBounds(start, end), { padding: [48, 48], maxZoom: 15 });
    setStatus("Could not load the road path. Showing a direct line instead.");
  } finally {
    findBtn.disabled = false;
  }
}

function revealLanding() {
  document.body.classList.remove("landing-intro");
  document.body.classList.add("landing-ready");

  window.setTimeout(() => {
    initMap();
    showRoute();
  }, 720);
}

if (formEl) {
  formEl.addEventListener("submit", (event) => {
    event.preventDefault();
    showRoute();
  });
}

startSelect.addEventListener("change", () => {
  if (mapReady) {
    showRoute();
  }
});
destSelect.addEventListener("change", () => {
  if (mapReady) {
    showRoute();
  }
});

function getFullscreenElement() {
  return (
    document.fullscreenElement ||
    document.webkitFullscreenElement ||
    document.msFullscreenElement ||
    null
  );
}

function isMapFullscreen() {
  return getFullscreenElement() === mapPane || mapPane.classList.contains("map-is-fullscreen");
}

function updateFullscreenButton() {
  const active = isMapFullscreen();
  const icon = fullscreenBtn.querySelector("i");
  fullscreenBtn.setAttribute("aria-pressed", String(active));
  fullscreenBtn.setAttribute("aria-label", active ? "Exit full screen map" : "View map fullscreen");
  icon.className = active ? "ri-fullscreen-exit-line" : "ri-fullscreen-line";
  window.setTimeout(() => {
    if (mapReady) {
      map.invalidateSize();
    }
  }, 80);
}

function enterMapFullscreen() {
  const request =
    mapPane.requestFullscreen ||
    mapPane.webkitRequestFullscreen ||
    mapPane.msRequestFullscreen;

  if (request) {
    const result = request.call(mapPane);
    if (result && typeof result.catch === "function") {
      result.catch(() => {
        mapPane.classList.add("map-is-fullscreen");
        updateFullscreenButton();
      });
    }
    return;
  }

  mapPane.classList.add("map-is-fullscreen");
  updateFullscreenButton();
}

function exitMapFullscreen() {
  const exit =
    document.exitFullscreen ||
    document.webkitExitFullscreen ||
    document.msExitFullscreen;

  if (getFullscreenElement() && exit) {
    exit.call(document);
    return;
  }

  mapPane.classList.remove("map-is-fullscreen");
  updateFullscreenButton();
}

function toggleMapFullscreen() {
  if (isMapFullscreen()) {
    exitMapFullscreen();
  } else {
    enterMapFullscreen();
  }
}

if (fullscreenBtn && mapPane) {
  fullscreenBtn.addEventListener("click", toggleMapFullscreen);
  document.addEventListener("fullscreenchange", updateFullscreenButton);
  document.addEventListener("webkitfullscreenchange", updateFullscreenButton);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && mapPane.classList.contains("map-is-fullscreen")) {
      exitMapFullscreen();
    }
  });
}

window.addEventListener("resize", () => {
  if (mapReady) {
    map.invalidateSize();
  }
});

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const introDelay = reduceMotion ? 0 : 2400;

window.addEventListener("load", () => {
  window.setTimeout(revealLanding, introDelay);
});
