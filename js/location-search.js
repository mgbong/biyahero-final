/**
 * location-search.js  —  Searchable location picker
 * ===================================================
 * Initialises every [data-location-picker] wrapper on the page.
 *
 * Public API (returned by initLocationPicker and stored on the element):
 *   picker.getSelected()          → loc object | null
 *   picker.setValue(loc)          → programmatically select a location
 *   picker.clear()                → clear input + selection
 *   picker.setError(msg)          → show red border + message
 *   picker.clearError()           → remove error state
 *
 * Events fired on the wrapper element (bubble up):
 *   "location-selected"  detail: loc   — user picked a location
 *   "location-cleared"               — input was manually cleared
 */

const TYPE_ICONS = {
  landmark: "ri-map-pin-2-line",
  terminal: "ri-bus-line",
  barangay: "ri-community-line",
};

const TYPE_LABELS = {
  landmark: "Landmark",
  terminal: "Terminal",
  barangay: "Barangay",
};

// ── Cache ─────────────────────────────────────────────────────────────────────
const _cache = {};

async function searchLocations(q) {
  const key = q.trim().toLowerCase();
  if (_cache[key] !== undefined) return _cache[key];
  try {
    const res  = await fetch(`/api/locations?q=${encodeURIComponent(key)}&limit=10`);
    const data = await res.json();
    _cache[key] = data.ok ? data.results : [];
  } catch (_) {
    _cache[key] = [];
  }
  return _cache[key];
}

// ── Dropdown builder ──────────────────────────────────────────────────────────
function buildDropdown(results, onSelect, highlightText) {
  const ul = document.createElement("ul");
  ul.className = "loc-dropdown";
  ul.setAttribute("role", "listbox");

  if (results.length === 0) {
    const li = document.createElement("li");
    li.className = "loc-dropdown__empty";
    li.innerHTML = `<i class="ri-search-line"></i> No locations found for "<strong>${highlightText}</strong>"`;
    ul.appendChild(li);
    return ul;
  }

  // Group by city
  const grouped = {};
  results.forEach(loc => {
    if (!grouped[loc.city]) grouped[loc.city] = [];
    grouped[loc.city].push(loc);
  });

  Object.entries(grouped).forEach(([city, locs]) => {
    const group = document.createElement("li");
    group.className = "loc-dropdown__group";
    group.setAttribute("role", "presentation");

    const cityLabel = document.createElement("span");
    cityLabel.className = "loc-dropdown__city";
    cityLabel.innerHTML = `<i class="ri-building-2-line"></i> ${city}`;
    group.appendChild(cityLabel);

    locs.forEach(loc => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "loc-dropdown__item";
      item.setAttribute("role", "option");
      item.setAttribute("data-name", loc.name);

      // Highlight matched text
      const hl = highlightText.trim();
      const re = hl ? new RegExp(`(${hl.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi") : null;
      const displayName = re ? loc.name.replace(re, "<mark>$1</mark>") : loc.name;

      item.innerHTML = `
        <span class="loc-dropdown__icon"><i class="${TYPE_ICONS[loc.type] || "ri-map-pin-line"}"></i></span>
        <span class="loc-dropdown__text">
          <span class="loc-dropdown__name">${displayName}</span>
          <span class="loc-dropdown__meta">${loc.barangay} · ${TYPE_LABELS[loc.type] || loc.type}</span>
        </span>
      `;

      item.addEventListener("mousedown", e => {
        e.preventDefault();
        onSelect(loc);
      });

      group.appendChild(item);
    });

    ul.appendChild(group);
  });

  return ul;
}

// ── Main initialiser ──────────────────────────────────────────────────────────
function initLocationPicker(wrapper) {
  const input       = wrapper.querySelector("[data-location-input]");
  const hiddenInput = wrapper.querySelector("[data-location-value]");
  // Error element may be a sibling of the wrapper (outside it), so search parent too
  const errorEl     = wrapper.querySelector("[data-location-error]")
                   || wrapper.parentElement?.querySelector("[data-location-error]");

  if (!input) return;

  let selectedLoc   = null;
  let dropdown      = null;
  let debounceTimer = null;

  // ── Error helpers ───────────────────────────────────────────────────────
  function setError(msg) {
    input.classList.add("loc-input--error");
    if (errorEl) { errorEl.textContent = msg; errorEl.hidden = false; }
  }

  function clearError() {
    input.classList.remove("loc-input--error");
    if (errorEl) { errorEl.textContent = ""; errorEl.hidden = true; }
  }

  // ── Dropdown helpers ────────────────────────────────────────────────────
  function closeDropdown() {
    dropdown?.remove();
    dropdown = null;
  }

  function openDropdown(results) {
    closeDropdown();
    dropdown = buildDropdown(results, selectLoc, input.value);
    wrapper.appendChild(dropdown);
  }

  // ── Select a location ───────────────────────────────────────────────────
  function selectLoc(loc) {
    selectedLoc = loc;
    input.value = loc.name;
    if (hiddenInput) hiddenInput.value = loc.name;
    wrapper.dataset.lat  = loc.lat;
    wrapper.dataset.lng  = loc.lng;
    wrapper.dataset.name = loc.name;
    clearError();
    closeDropdown();
    wrapper.dispatchEvent(new CustomEvent("location-selected", { bubbles: true, detail: loc }));
  }

  // ── Clear ───────────────────────────────────────────────────────────────
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

  // ── Input events ────────────────────────────────────────────────────────
  input.addEventListener("input", () => {
    const q = input.value.trim();
    clearTimeout(debounceTimer);

    // If user types after a selection, clear the selection (they're changing it)
    if (selectedLoc && input.value !== selectedLoc.name) {
      selectedLoc = null;
      if (hiddenInput) hiddenInput.value = "";
      delete wrapper.dataset.lat;
      delete wrapper.dataset.lng;
      delete wrapper.dataset.name;
      wrapper.dispatchEvent(new CustomEvent("location-cleared", { bubbles: true }));
    }

    if (q.length === 0) { closeDropdown(); return; }

    debounceTimer = setTimeout(async () => {
      const results = await searchLocations(q);
      openDropdown(results);
    }, 160);
  });

  input.addEventListener("focus", async () => {
    const results = await searchLocations(input.value.trim());
    openDropdown(results);
  });

  input.addEventListener("blur", () => {
    setTimeout(() => {
      closeDropdown();
      // If the user typed something but never selected, clear it to avoid partial text
      if (input.value.trim() && !selectedLoc) {
        input.value = "";
        if (hiddenInput) hiddenInput.value = "";
      }
    }, 160);
  });

  // ── Keyboard navigation ─────────────────────────────────────────────────
  input.addEventListener("keydown", e => {
    if (e.key === "Escape") { closeDropdown(); input.blur(); return; }
    if (!dropdown) return;

    const items   = [...dropdown.querySelectorAll(".loc-dropdown__item")];
    const focused = dropdown.querySelector(".loc-dropdown__item:focus");
    const idx     = items.indexOf(focused);

    if (e.key === "ArrowDown") { e.preventDefault(); (items[idx + 1] || items[0])?.focus(); }
    if (e.key === "ArrowUp")   { e.preventDefault(); (items[idx - 1] || items[items.length - 1])?.focus(); }
    if (e.key === "Enter" && focused) { e.preventDefault(); focused.dispatchEvent(new MouseEvent("mousedown")); }
  });

  // ── Public API on the wrapper element ───────────────────────────────────
  const api = {
    getSelected: ()    => selectedLoc,
    setValue:    (loc) => selectLoc(loc),
    clear:       ()    => clearPicker(),
    setError,
    clearError,
  };

  wrapper._locationPicker = api;
  return api;
}

// ── Auto-init all pickers on the page ─────────────────────────────────────────
window.LocationPickers = {};
document.querySelectorAll("[data-location-picker]").forEach(wrapper => {
  const id  = wrapper.id || wrapper.dataset.locationPicker;
  const api = initLocationPicker(wrapper);
  if (id && api) window.LocationPickers[id] = api;
});
