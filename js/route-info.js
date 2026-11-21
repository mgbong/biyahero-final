/**
 * route-info.js — public Route catalog (guest-friendly)
 * Offline: caches last list in localStorage with "may be outdated" label.
 */
const CACHE_KEY = "biyahero_route_info_cache";
const listEl = document.querySelector("#routes-grid");
const countEl = document.querySelector("#count-badge");
const searchEl = document.querySelector("#route-search");
const bannerEl = document.querySelector("#advisory-banner");
const detailEl = document.querySelector("#route-detail-panel");

function fmtLocal(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-PH", { timeZone: "Asia/Manila" }) + " (PHT)";
  } catch {
    return iso;
  }
}

function modeLabel(mode) {
  return (mode || "").replace(/_/g, " ");
}

function renderBanner(advisories) {
  if (!bannerEl) return;
  if (!advisories.length) {
    bannerEl.hidden = true;
    bannerEl.innerHTML = "";
    return;
  }
  bannerEl.hidden = false;
  bannerEl.innerHTML = advisories
    .slice(0, 3)
    .map(
      (a) => `
    <div class="ri-banner ri-banner--${a.severity}" role="status">
      <i class="ri-alarm-warning-line" aria-hidden="true"></i>
      <div>
        <strong>${a.severity_label}: ${a.title}</strong>
        <p>${a.description}</p>
        <span class="ri-meta">Affects ${a.affected_routes.join(", ") || "area"} · Updated ${fmtLocal(a.last_updated)}</span>
      </div>
    </div>`
    )
    .join("");
}

function renderRoutes(routes, { staleOffline = false } = {}) {
  if (!listEl) return;
  if (!routes.length) {
    listEl.innerHTML = `<div class="ri-empty" role="status">No routes match your search.</div>`;
    if (countEl) countEl.innerHTML = `<i class="ri-route-line"></i> 0 routes`;
    return;
  }
  if (countEl) {
    countEl.innerHTML = `<i class="ri-route-line"></i> ${routes.length} route(s)${
      staleOffline ? " · may be outdated (offline cache)" : ""
    }`;
  }
  listEl.innerHTML = routes
    .map((r) => {
      const badge = r.verified
        ? `<span class="ri-badge ri-badge--ok" title="Verified by ${r.verification.by || "staff"}">Verified</span>`
        : `<span class="ri-badge ri-badge--warn">Unverified</span>`;
      const stale = r.stale_warning
        ? `<span class="ri-badge ri-badge--stale">Needs review</span>`
        : "";
      const stops = (r.stops || []).map((s) => `<li>${s.name}</li>`).join("");
      const adv = (r.active_advisories || [])
        .map((a) => `<span class="ri-chip">${a.severity_label}: ${a.title}</span>`)
        .join("");
      return `
      <article class="ri-card" data-code="${r.code}">
        <div class="ri-card__top">
          <div>
            <span class="ri-code">${r.code}</span>
            <h2 class="ri-name">${r.name}</h2>
          </div>
          <div class="ri-badges">${badge}${stale}</div>
        </div>
        <p class="ri-dir">${r.terminals?.start || "—"} → ${r.terminals?.end || "—"}</p>
        <div class="ri-meta-row">
          <span class="ri-chip">${modeLabel(r.mode)}</span>
          <span>${r.fare_reference || "Fare ref n/a"}</span>
          <span>Every ~${r.frequency_min || "?"} min</span>
          <span>${r.hours?.from || "?"}–${r.hours?.to || "?"}</span>
        </div>
        ${adv ? `<div class="ri-adv-row">${adv}</div>` : ""}
        <details class="ri-details">
          <summary>Stops & source</summary>
          <ol>${stops}</ol>
          <p class="ri-source">Last updated: ${fmtLocal(r.last_updated)}</p>
          <p class="ri-source">Source: ${r.source?.label || "—"}
            ${r.source?.url ? ` · <a href="${r.source.url}" target="_blank" rel="noopener">Open source</a>` : ""}
          </p>
          ${
            r.verified
              ? `<p class="ri-source">Verified by ${r.verification.by} on ${fmtLocal(r.verification.at)}</p>`
              : ""
          }
          <a class="sm-btn sm-btn--glass" href="report.html?route=${encodeURIComponent(r.code)}">Report a problem</a>
        </details>
      </article>`;
    })
    .join("");
}

async function load() {
  const q = searchEl?.value?.trim() || "";
  try {
    const res = await fetch(`/api/route-info?q=${encodeURIComponent(q)}`, { credentials: "same-origin" });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Load failed");
    // Attach advisories per route for chips
    const byCode = {};
    (data.advisories || []).forEach((a) => {
      (a.affected_routes || []).forEach((c) => {
        byCode[c] = byCode[c] || [];
        byCode[c].push(a);
      });
    });
    data.routes.forEach((r) => {
      r.active_advisories = byCode[r.code] || [];
    });
    localStorage.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), routes: data.routes, advisories: data.advisories }));
    renderBanner(data.advisories || []);
    renderRoutes(data.routes);
  } catch (err) {
    const raw = localStorage.getItem(CACHE_KEY);
    if (raw) {
      const cached = JSON.parse(raw);
      renderBanner(cached.advisories || []);
      renderRoutes(cached.routes || [], { staleOffline: true });
    } else if (listEl) {
      listEl.innerHTML = `<div class="ri-empty" role="alert">Could not load routes. Check your connection.</div>`;
    }
  }
}

searchEl?.addEventListener("input", () => {
  clearTimeout(searchEl._t);
  searchEl._t = setTimeout(load, 250);
});

load();
