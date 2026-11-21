/**
 * advisories.js — Route & Traffic Updates
 * Separates verified route changes from general traffic advisories.
 * Shows data source + refresh frequency from /api/updates.
 */

const listEl = document.querySelector("#updates-list");
const changesEl = document.querySelector("#route-changes-list");
const countEl = document.querySelector("#count-badge");
const filterView = document.querySelector("#filter-view");
const filterSev = document.querySelector("#filter-severity");
const historyToggle = document.querySelector("#filter-history");
const refreshLabelEl = document.querySelector("#upd-refresh-label");
const lastDataEl = document.querySelector("#upd-last-data");
const sourcesBody = document.querySelector("#upd-sources-body");
const sectionChanges = document.querySelector("#section-route-changes");
const sectionTraffic = document.querySelector("#section-traffic");

let refreshTimer = null;
let refreshSeconds = 60;

function fmtLocal(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-PH", { timeZone: "Asia/Manila" }) + " (PHT)";
  } catch {
    return iso;
  }
}

function iconFor(sev) {
  if (sev === "critical") return "ri-error-warning-fill";
  if (sev === "warning") return "ri-alarm-warning-line";
  return "ri-information-line";
}

function toneFor(sev) {
  if (sev === "critical") return "obstruction";
  if (sev === "warning") return "moderate";
  return "normal";
}

function sourceBlock(src) {
  if (!src) return `<p class="ri-source">Source: —</p>`;
  const link = src.url
    ? ` · <a href="${src.url}" target="_blank" rel="noopener">Open source</a>`
    : "";
  return `
    <p class="ri-source">
      <strong>Source:</strong> ${src.label || "—"}
      ${src.blurb ? ` — ${src.blurb}` : ""}
      ${link}
    </p>`;
}

function renderRouteChanges(items) {
  if (!changesEl) return;
  if (!items.length) {
    changesEl.innerHTML = `
      <div class="ri-empty" role="status">
        No verified route changes right now.
        <span class="ri-muted">Plan Trip is using the usual published lines.</span>
      </div>`;
    return;
  }
  changesEl.innerHTML = items
    .map((r) => {
      const badge = r.verified
        ? `<span class="ri-badge ri-badge--ok">Verified route change</span>`
        : `<span class="ri-badge ri-badge--warn">Unverified</span>`;
      return `
    <article class="ri-card upd-card upd-card--verified" aria-label="Verified route change: ${r.title}">
      <div class="ri-card__top">
        <div>
          <span class="ri-code">${r.route_code || "—"}</span>
          <h3 class="ri-name">${r.title}</h3>
        </div>
        <div class="ri-badges">
          ${badge}
          <span class="ri-badge">${r.change_type_label || r.change_type}</span>
        </div>
      </div>
      <p>${r.description || ""}</p>
      <p class="ri-meta"><strong>Usual path:</strong> ${(r.original_stops || []).join(" → ") || "—"}</p>
      <p class="ri-meta"><strong>New / detour:</strong> ${(r.detour_stops || []).join(" → ") || "—"}</p>
      ${r.affected_stops ? `<p class="ri-meta"><strong>Affected stops:</strong> ${r.affected_stops}</p>` : ""}
      ${sourceBlock(r.source)}
      <p class="ri-source">
        <i class="ri-time-line" aria-hidden="true"></i>
        Active: ${fmtLocal(r.starts_at)} →
        ${r.until_further_notice ? "until further notice" : fmtLocal(r.ends_at)}
        · Last updated: ${fmtLocal(r.last_updated)}
      </p>
    </article>`;
    })
    .join("");
}

function renderTraffic(advisories) {
  if (!listEl) return;
  if (!advisories.length) {
    listEl.innerHTML = `<div class="ri-empty" role="status">No active traffic advisories.</div>`;
    if (countEl) countEl.innerHTML = `<i class="ri-notification-line"></i> 0 traffic advisories`;
    return;
  }
  if (countEl) {
    countEl.innerHTML = `<i class="ri-notification-line"></i> ${advisories.length} traffic advisory item(s)`;
  }
  listEl.innerHTML = advisories
    .map((a) => {
      const tone = toneFor(a.severity);
      const serviceNote =
        a.bucket === "service_advisory"
          ? `<span class="ri-badge">Service notice</span>`
          : `<span class="ri-badge ri-badge--warn">Traffic advisory</span>`;
      return `
    <article class="status-card status-card--${tone} upd-card upd-card--traffic"
      aria-label="Traffic advisory, ${a.severity_label}: ${a.title}">
      <div class="status-card__title">
        <i class="${iconFor(a.severity)}" aria-hidden="true"></i>
        ${a.title}
        <span class="badge badge-${tone}">${a.severity_label}</span>
        ${serviceNote}
      </div>
      <div class="status-card__desc">${a.description}</div>
      <div class="status-card__meta">
        Type: ${a.type_label || a.type}
        · Routes: ${(a.affected_routes || []).join(", ") || "General area"}
        ${a.affected_stops ? ` · Stops: ${a.affected_stops}` : ""}
      </div>
      ${sourceBlock(a.source)}
      <div class="status-card__footer">
        <i class="ri-time-line" aria-hidden="true"></i>
        ${fmtLocal(a.starts_at)} → ${a.ends_at ? fmtLocal(a.ends_at) : "until further notice"}
        · Last updated: ${fmtLocal(a.last_updated)}
      </div>
    </article>`;
    })
    .join("");
}

function renderMeta(meta) {
  if (!meta) return;
  refreshSeconds = meta.refresh_seconds || 60;
  if (refreshLabelEl) {
    refreshLabelEl.textContent =
      meta.refresh_label ||
      `This page checks for new posts about every ${refreshSeconds} seconds.`;
  }
  if (lastDataEl) {
    lastDataEl.textContent = meta.last_data_at
      ? `Newest post in feed: ${fmtLocal(meta.last_data_at)}. ${meta.publish_sla || ""}`
      : `No posts in this feed yet. ${meta.publish_sla || ""}`;
  }
  if (sourcesBody) {
    const cats = meta.categories || {};
    sourcesBody.innerHTML = `
      <p><strong>Verified route change:</strong> ${cats.route_change || ""}</p>
      <p><strong>Traffic advisory:</strong> ${cats.traffic_advisory || ""}</p>
      <p><strong>Refresh:</strong> ${meta.refresh_label || ""} ${meta.publish_sla || ""}</p>
      <p><strong>Time zone:</strong> ${meta.timezone || "Asia/Manila"}</p>
      <ul>
        ${(meta.sources || [])
          .map(
            (s) =>
              `<li><strong>${s.label}</strong> (${s.trust}) — ${s.blurb}</li>`
          )
          .join("")}
      </ul>`;
  }
}

function applyViewFilter() {
  const view = filterView?.value || "all";
  if (sectionChanges) sectionChanges.hidden = view === "traffic";
  if (sectionTraffic) sectionTraffic.hidden = view === "route_changes";
}

async function load() {
  const history = historyToggle?.checked ? "1" : "0";
  const sev = filterSev?.value || "";
  applyViewFilter();
  try {
    const res = await fetch(
      `/api/updates?history=${history}${sev ? `&severity=${encodeURIComponent(sev)}` : ""}`,
      { credentials: "same-origin" }
    );
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Load failed");
    renderMeta(data.meta);
    renderRouteChanges(data.route_changes || []);
    renderTraffic(data.traffic_advisories || []);
    scheduleRefresh();
  } catch {
    if (listEl) {
      listEl.innerHTML = `<div class="ri-empty" role="alert">Could not load updates. Check your connection.</div>`;
    }
    if (changesEl) {
      changesEl.innerHTML = `<div class="ri-empty" role="alert">Could not load route changes.</div>`;
    }
  }
}

function scheduleRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(load, Math.max(15, refreshSeconds) * 1000);
}

[filterView, filterSev, historyToggle].forEach((el) =>
  el?.addEventListener("change", load)
);

load();
