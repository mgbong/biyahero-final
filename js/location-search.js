/**
 * location-search.js — Location autocomplete (data layer + UI)
 * ============================================================
 * Layers:
 *   Data  → searchLocations(), reverseGeocode(), saveRecent(), getRecents()
 *   UI    → initLocationPicker() for each [data-location-picker]
 *
 * Public API on each picker:
 *   getSelected(), setValue(loc), clear(), setError(msg), clearError()
 *
 * Events (bubble): location-selected, location-cleared
 */

const TYPE_ICONS = {
  landmark: "ri-map-pin-2-line",
  terminal: "ri-bus-line",
  barangay: "ri-community-line",
  current: "ri-crosshair-2-line",
  map: "ri-map-pin-add-line",
};

const TYPE_LABELS = {
  landmark: "Landmark",
  terminal: "Terminal",
  barangay: "Barangay",
  current: "My location",
  map: "Map pin",
};

const DEBOUNCE_MS = 350;
const RECENT_KEY = "biyahero_recent_places";
const RECENT_MAX = 5;

const _cache = {};

/** Data: search local catalog */
async function searchLocations(q) {
  const key = (q || "").trim().toLowerCase();
  if (_cache[key] !== undefined) return { ok: true, results: _cache[key], error: null };

  try {
    const res = await fetch(`/api/locations?q=${encodeURIComponent(key)}&limit=10`, {
      credentials: "same-origin",
    });
    if (!res.ok) {
      return { ok: false, results: [], error: "Could not search right now. Try again." };
    }
    const data = await res.json();
    const results = data.ok ? data.results : [];
    _cache[key] = results;
    return { ok: true, results, error: null };
  } catch (_) {
    return { ok: false, results: [], error: "No internet. Check your connection and try again." };
  }
}

/** Data: reverse geocode via our Flask proxy (Nominatim) */
async function reverseGeocode(lat, lng) {
  try {
    const res = await fetch(
      `/api/geocode/reverse?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`,
      { credentials: "same-origin" }
    );
    const data = await res.json();
    if (!data.ok) return null;
    return data.place;
  } catch (_) {
    return null;
  }
}

function getRecents() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
  } catch (_) {
    return [];
  }
}

function saveRecent(loc) {
  if (!loc || !loc.name) return;
  const list = getRecents().filter((r) => r.name !== loc.name);
  list.unshift({
    name: loc.name,
    type: loc.type || "landmark",
    city: loc.city || "",
    barangay: loc.barangay || "",
    lat: loc.lat,
    lng: loc.lng,
  });
  localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, RECENT_MAX)));
}

function buildDropdown(results, onSelect, highlightText, emptyMsg) {
  const ul = document.createElement("ul");
  ul.className = "loc-dropdown";
  ul.setAttribute("role", "listbox");

  if (!results.length) {
    const li = document.createElement("li");
    li.className = "loc-dropdown__empty";
    li.innerHTML = `<i class="ri-search-line" aria-hidden="true"></i> ${emptyMsg || `No places found for "<strong></strong>"`}`;
    if (highlightText && !emptyMsg) {
      li.querySelector("strong").textContent = highlightText;
    }
    ul.appendChild(li);
    return ul;
  }

  const grouped = {};
  results.forEach((loc) => {
    const city = loc.city || "Saved";
    if (!grouped[city]) grouped[city] = [];
    grouped[city].push(loc);
  });

  Object.entries(grouped).forEach(([city, locs]) => {
    const group = document.createElement("li");
    group.className = "loc-dropdown__group";
    group.setAttribute("role", "presentation");

    const cityLabel = document.createElement("span");
    cityLabel.className = "loc-dropdown__city";
    cityLabel.innerHTML = `<i class="ri-building-2-line" aria-hidden="true"></i> ${city}`;
    group.appendChild(cityLabel);

    locs.forEach((loc) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "loc-dropdown__item";
      item.setAttribute("role", "option");

      const hl = (highlightText || "").trim();
      const re = hl ? new RegExp(`(${hl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi") : null;
      const safeName = loc.name.replace(/</g, "&lt;");
      const displayName = re ? safeName.replace(re, "<mark>$1</mark>") : safeName;

      item.innerHTML = `
        <span class="loc-dropdown__icon"><i class="${TYPE_ICONS[loc.type] || "ri-map-pin-line"}" aria-hidden="true"></i></span>
        <span class="loc-dropdown__text">
          <span class="loc-dropdown__name">${displayName}</span>
          <span class="loc-dropdown__meta">${loc.barangay || loc.address || ""} · ${TYPE_LABELS[loc.type] || loc.type || "Place"}</span>
        </span>
      `;

      item.addEventListener("mousedown", (e) => {
        e.preventDefault();
        onSelect(loc);
      });

      group.appendChild(item);
    });

    ul.appendChild(group);
  });

  return ul;
}

function initLocationPicker(wrapper) {
  const input = wrapper.querySelector("[data-location-input]");
  const hiddenInput = wrapper.querySelector("[data-location-value]");
  const errorEl =
    wrapper.querySelector("[data-location-error]") ||
    wrapper.parentElement?.querySelector("[data-location-error]");

  if (!input) return null;

  let selectedLoc = null;
  let dropdown = null;
  let debounceTimer = null;

  function setError(msg) {
    input.classList.add("loc-input--error");
    if (errorEl) {
      errorEl.textContent = msg;
      errorEl.hidden = false;
    }
  }

  function clearError() {
    input.classList.remove("loc-input--error");
    if (errorEl) {
      errorEl.textContent = "";
      errorEl.hidden = true;
    }
  }

  function closeDropdown() {
    dropdown?.remove();
    dropdown = null;
  }

  function openDropdown(results, emptyMsg) {
    closeDropdown();
    dropdown = buildDropdown(results, selectLoc, input.value, emptyMsg);
    wrapper.appendChild(dropdown);
  }

  function selectLoc(loc) {
    selectedLoc = loc;
    input.value = loc.name;
    if (hiddenInput) hiddenInput.value = loc.name;
    wrapper.dataset.lat = loc.lat;
    wrapper.dataset.lng = loc.lng;
    wrapper.dataset.name = loc.name;
    clearError();
    closeDropdown();
    saveRecent(loc);
    wrapper.dispatchEvent(new CustomEvent("location-selected", { bubbles: true, detail: loc }));
  }

  function clearPicker() {
    selectedLoc = null;
    input.value = "";
    if (hiddenInput) hiddenInput.value = "";
    delete wrapper.dataset.lat;
    delete wrapper.dataset.lng;
    delete wrapper.dataset.name;
    clearError();
    closeDropdown();
    wrapper.dispatchEvent(new CustomEvent("location-cleared", { bubbles: true }));
  }

  input.addEventListener("input", () => {
    const q = input.value.trim();
    clearTimeout(debounceTimer);

    if (selectedLoc && input.value !== selectedLoc.name) {
      selectedLoc = null;
      if (hiddenInput) hiddenInput.value = "";
      delete wrapper.dataset.lat;
      delete wrapper.dataset.lng;
      delete wrapper.dataset.name;
      wrapper.dispatchEvent(new CustomEvent("location-cleared", { bubbles: true }));
    }

    if (q.length === 0) {
      const recents = getRecents();
      if (recents.length) openDropdown(recents);
      else closeDropdown();
      return;
    }

    debounceTimer = setTimeout(async () => {
      const { ok, results, error } = await searchLocations(q);
      if (!ok) {
        openDropdown([], error);
        return;
      }
      openDropdown(
        results,
        results.length ? null : `No places found for "${q}". Try another name or pick on the map.`
      );
    }, DEBOUNCE_MS);
  });

  input.addEventListener("focus", async () => {
    const q = input.value.trim();
    if (!q) {
      const recents = getRecents();
      if (recents.length) openDropdown(recents);
      return;
    }
    const { ok, results, error } = await searchLocations(q);
    openDropdown(ok ? results : [], ok ? null : error);
  });

  input.addEventListener("blur", () => {
    setTimeout(() => {
      closeDropdown();
      if (input.value.trim() && !selectedLoc) {
        input.value = "";
        if (hiddenInput) hiddenInput.value = "";
      }
    }, 180);
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeDropdown();
      input.blur();
      return;
    }
    if (!dropdown) return;
    const items = [...dropdown.querySelectorAll(".loc-dropdown__item")];
    const focused = dropdown.querySelector(".loc-dropdown__item:focus");
    const idx = items.indexOf(focused);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      (items[idx + 1] || items[0])?.focus();
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      (items[idx - 1] || items[items.length - 1])?.focus();
    }
    if (e.key === "Enter" && focused) {
      e.preventDefault();
      focused.dispatchEvent(new MouseEvent("mousedown"));
    }
  });

  const api = {
    getSelected: () => selectedLoc,
    setValue: (loc) => selectLoc(loc),
    clear: () => clearPicker(),
    setError,
    clearError,
  };

  wrapper._locationPicker = api;
  return api;
}

window.LocationSearch = {
  searchLocations,
  reverseGeocode,
  getRecents,
  saveRecent,
};

window.LocationPickers = {};
document.querySelectorAll("[data-location-picker]").forEach((wrapper) => {
  const id = wrapper.id || wrapper.dataset.locationPicker;
  const api = initLocationPicker(wrapper);
  if (id && api) window.LocationPickers[id] = api;
});
