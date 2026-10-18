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
const mapEl = document.querySelector("#trip-map");

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

function setStatus(message) {
  statusEl.textContent = message;
}

function latLngToLonLat(latLng) {
  return `${latLng[1]},${latLng[0]}`;
}

function decodePolyline(encoded) {
  let index = 0;
  let lat = 0;
  let lng = 0;
  const coordinates = [];

  while (index < encoded.length) {
    let result = 0;
    let shift = 0;
    let byte;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    lat += result & 1 ? ~(result >> 1) : result >> 1;

    result = 0;
    shift = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    lng += result & 1 ? ~(result >> 1) : result >> 1;
    coordinates.push([lat / 1e5, lng / 1e5]);
  }

  return coordinates;
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

  if (!route) {
    throw new Error("No driving route found");
  }

  if (route.geometry && route.geometry.coordinates) {
    return {
      latLngs: route.geometry.coordinates.map(([lon, lat]) => [lat, lon]),
      distanceKm: route.distance / 1000,
      durationMin: Math.round(route.duration / 60),
    };
  }

  if (typeof route.geometry === "string") {
    return {
      latLngs: decodePolyline(route.geometry),
      distanceKm: route.distance / 1000,
      durationMin: Math.round(route.duration / 60),
    };
  }

  throw new Error("Route geometry missing");
}

function drawRoute(startName, destName, start, end, latLngs, distanceKm, durationMin) {
  routeLayer.clearLayers();

  const line = L.polyline(latLngs, {
    color: "#087c6d",
    weight: 6,
    opacity: 0.9,
    lineJoin: "round",
    lineCap: "round",
  }).addTo(routeLayer);

  L.circleMarker(start, {
    radius: 8,
    color: "#076b60",
    fillColor: "#087c6d",
    fillOpacity: 1,
    weight: 2,
  })
    .bindPopup(`<strong>Start</strong><br>${startName}`)
    .addTo(routeLayer);

  L.circleMarker(end, {
    radius: 8,
    color: "#9b2c2c",
    fillColor: "#ef4444",
    fillOpacity: 1,
    weight: 2,
  })
    .bindPopup(`<strong>Destination</strong><br>${destName}`)
    .addTo(routeLayer);

  map.fitBounds(line.getBounds(), { padding: [36, 36], maxZoom: 16 });
  map.invalidateSize();

  setStatus(
    `${startName} → ${destName} · follows roads · ~${distanceKm.toFixed(1)} km · ~${durationMin} min`
  );
}

async function showRoute() {
  const startName = startSelect.value;
  const destName = destSelect.value;
  const start = PLACE_COORDS[startName];
  const end = PLACE_COORDS[destName];

  if (!start || !end) {
    setStatus("Choose a listed starting point and destination.");
    return;
  }

  if (startName === destName) {
    routeLayer.clearLayers();
    L.circleMarker(start, {
      radius: 8,
      color: "#076b60",
      fillColor: "#087c6d",
      fillOpacity: 1,
      weight: 2,
    })
      .bindPopup(`<strong>${startName}</strong>`)
      .addTo(routeLayer);
    map.setView(start, 16);
    setStatus("Starting point and destination are the same.");
    return;
  }

  findBtn.disabled = true;
  setStatus(`Tracing the road route from ${startName} to ${destName}…`);

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
    L.circleMarker(start, { radius: 8, color: "#076b60", fillColor: "#087c6d", fillOpacity: 1 }).addTo(routeLayer);
    L.circleMarker(end, { radius: 8, color: "#9b2c2c", fillColor: "#ef4444", fillOpacity: 1 }).addTo(routeLayer);
    map.fitBounds(L.latLngBounds(start, end), { padding: [36, 36], maxZoom: 16 });
    setStatus("Could not load the road path. Showing a direct line instead.");
  } finally {
    findBtn.disabled = false;
  }
}

findBtn.addEventListener("click", showRoute);
window.addEventListener("load", () => {
  map.invalidateSize();
  showRoute();
});
