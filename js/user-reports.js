/**
 * user-reports.js — submit + my reports (login required to send)
 * Guests see login CTA; context kept in sessionStorage + query string.
 */
const CONTEXT_KEY = "biyahero_report_draft";
const formSection = document.querySelector("#form-section");
const guestGate = document.querySelector("#guest-gate");
const formError = document.querySelector("#form-error");
const form = document.querySelector("#report-form");
const similarBox = document.querySelector("#similar-box");
const myList = document.querySelector("#my-reports-list");
const confirmEl = document.querySelector("#report-confirm");

function params() {
  return new URLSearchParams(location.search);
}

function saveDraft(extra = {}) {
  const draft = {
    category: document.querySelector("#report-category")?.value,
    route_code: document.querySelector("#report-route")?.value,
    stop_name: document.querySelector("#report-stop")?.value,
    description: document.querySelector("#report-desc")?.value,
    suggested_correction: document.querySelector("#report-suggest")?.value,
    ...extra,
  };
  sessionStorage.setItem(CONTEXT_KEY, JSON.stringify(draft));
}

function restoreDraft() {
  const p = params();
  const raw = sessionStorage.getItem(CONTEXT_KEY);
  let draft = {};
  try {
    draft = raw ? JSON.parse(raw) : {};
  } catch {
    draft = {};
  }
  if (p.get("route")) draft.route_code = p.get("route");
  if (p.get("stop")) draft.stop_name = p.get("stop");
  if (p.get("category")) draft.category = p.get("category");
  const set = (id, v) => {
    const el = document.querySelector(id);
    if (el && v != null) el.value = v;
  };
  set("#report-category", draft.category);
  set("#report-route", draft.route_code);
  set("#report-stop", draft.stop_name);
  set("#report-desc", draft.description);
  set("#report-suggest", draft.suggested_correction);
}

async function ensureAuthUI() {
  const user = window.biyaheroUser;
  if (!user) {
    if (guestGate) guestGate.hidden = false;
    if (formSection) formSection.hidden = true;
    const next = encodeURIComponent("/html/report.html" + location.search);
    guestGate?.querySelectorAll("[data-login]").forEach((a) => {
      a.href = `/html/login.html?next=${next}`;
    });
    guestGate?.querySelectorAll("[data-signup]").forEach((a) => {
      a.href = `/html/commuter-signup.html?next=${next}`;
    });
    return false;
  }
  if (guestGate) guestGate.hidden = true;
  if (formSection) formSection.hidden = false;
  return true;
}

function showError(msg) {
  if (!formError) return;
  formError.textContent = msg || "";
  formError.hidden = !msg;
}

async function loadMine() {
  if (!myList || !window.biyaheroUser) return;
  try {
    const res = await fetch("/api/reports/mine", { credentials: "same-origin" });
    const data = await res.json();
    if (!data.ok) {
      myList.innerHTML = `<p class="ri-muted">${data.error || "Could not load."}</p>`;
      return;
    }
    if (!data.reports.length) {
      myList.innerHTML = `<p class="ri-empty">No reports yet.</p>`;
      return;
    }
    myList.innerHTML = data.reports
      .map(
        (r) => `
      <article class="ri-card" data-id="${r.id}">
        <div class="ri-card__top">
          <strong>${r.ref_code}</strong>
          <span class="ri-badge">${r.status.replace(/_/g, " ")}</span>
        </div>
        <p>${r.category_label}${r.route_code ? ` · ${r.route_code}` : ""}</p>
        <p class="ri-meta">${new Date(r.created_at).toLocaleString("en-PH", { timeZone: "Asia/Manila" })}</p>
        <button type="button" class="trip-mini-btn" data-open="${r.id}">Open</button>
      </article>`
      )
      .join("");
    myList.querySelectorAll("[data-open]").forEach((btn) => {
      btn.addEventListener("click", () => openDetail(btn.getAttribute("data-open")));
    });
  } catch {
    myList.innerHTML = `<p class="ri-empty">Could not load your reports.</p>`;
  }
}

async function openDetail(id) {
  const panel = document.querySelector("#report-detail");
  if (!panel) return;
  const res = await fetch(`/api/reports/${id}`, { credentials: "same-origin" });
  const data = await res.json();
  if (!data.ok) {
    panel.innerHTML = `<p role="alert">${data.error}</p>`;
    return;
  }
  const r = data.report;
  panel.hidden = false;
  panel.innerHTML = `
    <h3>${r.ref_code} · ${r.status.replace(/_/g, " ")}</h3>
    <p>${r.description}</p>
    <ol class="ri-timeline">
      ${(r.timeline || [])
        .map((t) => `<li><strong>${t.to}</strong> — ${t.note || ""} <em>${t.at}</em></li>`)
        .join("")}
    </ol>
    ${
      ["submitted", "needs_more_info", "under_review"].includes(r.status)
        ? `<div class="trip-field-actions">
            <button type="button" class="trip-mini-btn" id="btn-add-note">Add info</button>
            <button type="button" class="trip-mini-btn" id="btn-withdraw">Withdraw</button>
          </div>`
        : ""
    }`;
  panel.querySelector("#btn-withdraw")?.addEventListener("click", async () => {
    await fetch(`/api/reports/${id}/status`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "withdrawn" }),
    });
    loadMine();
    openDetail(id);
  });
  panel.querySelector("#btn-add-note")?.addEventListener("click", async () => {
    const body = prompt("Add more information:");
    if (!body) return;
    await fetch(`/api/reports/${id}/note`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    openDetail(id);
  });
}

async function submitReport(confirmSimilar = false) {
  showError("");
  saveDraft();
  const payload = {
    category: document.querySelector("#report-category").value,
    route_code: document.querySelector("#report-route").value || null,
    stop_name: document.querySelector("#report-stop").value || null,
    description: document.querySelector("#report-desc").value,
    suggested_correction: document.querySelector("#report-suggest").value || null,
    observed_at: document.querySelector("#report-when")?.value || null,
    confirm_similar: confirmSimilar,
  };
  const lat = document.querySelector("#report-lat")?.value;
  const lng = document.querySelector("#report-lng")?.value;
  if (lat && lng) {
    payload.lat = parseFloat(lat);
    payload.lng = parseFloat(lng);
  }

  const fd = new FormData();
  Object.entries(payload).forEach(([k, v]) => {
    if (v != null && v !== "") fd.append(k, v === true ? "1" : String(v));
  });
  const photos = document.querySelector("#report-photos")?.files;
  if (photos) {
    [...photos].slice(0, 3).forEach((f) => fd.append("photos", f));
  }

  const res = await fetch("/api/reports", { method: "POST", credentials: "same-origin", body: fd });
  const data = await res.json();
  if (data.needs_confirm) {
    if (similarBox) {
      similarBox.hidden = false;
      similarBox.innerHTML = `
        <p><strong>Similar reports exist</strong></p>
        <ul>${(data.similar || [])
          .map((s) => `<li>${s.ref_code} · ${s.status} · ${s.route_code || ""}</li>`)
          .join("")}</ul>
        <button type="button" class="sm-btn sm-btn--orange" id="confirm-similar">Send anyway</button>`;
      similarBox.querySelector("#confirm-similar")?.addEventListener("click", () => submitReport(true));
    }
    showError(data.error);
    return;
  }
  if (!data.ok) {
    showError(data.error || "Could not send.");
    if (data.login_required) {
      saveDraft();
      location.href = data.redirect || "/html/login.html?next=/html/report.html";
    }
    return;
  }
  sessionStorage.removeItem(CONTEXT_KEY);
  if (confirmEl) {
    confirmEl.hidden = false;
    confirmEl.innerHTML = `<div class="ri-confirm" role="status">
      <i class="ri-checkbox-circle-line" aria-hidden="true"></i>
      <div><strong>Report sent</strong><p>Reference: ${data.report.ref_code}</p></div>
    </div>`;
  }
  form?.reset();
  if (similarBox) similarBox.hidden = true;
  loadMine();
}

form?.addEventListener("submit", (e) => {
  e.preventDefault();
  submitReport(false);
});

document.querySelector("#use-my-location")?.addEventListener("click", () => {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition((pos) => {
    const lat = document.querySelector("#report-lat");
    const lng = document.querySelector("#report-lng");
    if (lat) lat.value = pos.coords.latitude.toFixed(5);
    if (lng) lng.value = pos.coords.longitude.toFixed(5);
  });
});

// Offline draft autosave
["#report-category", "#report-route", "#report-stop", "#report-desc", "#report-suggest"].forEach((sel) => {
  document.querySelector(sel)?.addEventListener("change", () => saveDraft());
  document.querySelector(sel)?.addEventListener("input", () => saveDraft());
});

(async function boot() {
  // wait a tick for user-soft.js
  await new Promise((r) => setTimeout(r, 50));
  restoreDraft();
  const ok = await ensureAuthUI();
  if (ok) loadMine();
})();
