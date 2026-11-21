/**
 * staff-desk.js — operator/admin maintenance UI
 */
const statusEl = document.querySelector("#staff-status");

async function api(url, opts) {
  const res = await fetch(url, { credentials: "same-origin", ...opts });
  const data = await res.json();
  return { res, data };
}

async function loadQueue() {
  const { res, data } = await api("/api/staff/queue");
  const box = document.querySelector("#approval-queue");
  if (!data.ok) {
    statusEl.textContent = data.error || "Staff login required (operator).";
    box.textContent = data.error;
    return;
  }
  statusEl.textContent = data.is_admin ? "Admin powers on." : "Operator mode (drafts need admin approval).";
  const rows = (data.approvals || [])
    .map(
      (a) => `
    <div class="ri-card">
      <strong>${a.entity_type} #${a.entity_id}</strong>
      <p class="ri-meta">by ${a.requested_by_name} · ${a.created_at}</p>
      ${
        data.is_admin
          ? `<button type="button" class="trip-mini-btn" data-approve="${a.entity_type}:${a.entity_id}">Approve</button>
             <button type="button" class="trip-mini-btn" data-reject="${a.entity_type}:${a.entity_id}">Reject</button>`
          : `<span class="ri-badge">Pending review</span>`
      }
    </div>`
    )
    .join("") || "<p class='ri-empty'>Queue is empty.</p>";
  box.innerHTML = rows;
  box.querySelectorAll("[data-approve]").forEach((btn) => {
    btn.addEventListener("click", () => review(btn.getAttribute("data-approve"), true));
  });
  box.querySelectorAll("[data-reject]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const note = prompt("Reject reason (required):");
      if (!note) return;
      review(btn.getAttribute("data-reject"), false, note);
    });
  });
}

async function review(key, approve, note = "") {
  const [entity_type, entity_id] = key.split(":");
  const { data } = await api("/api/staff/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entity_type, entity_id: Number(entity_id), approve, note }),
  });
  alert(data.ok ? `Done: ${data.result}` : data.error);
  loadQueue();
}

document.querySelector("#rr-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    route_code: document.querySelector("#rr-code").value.trim(),
    change_type: document.querySelector("#rr-type").value,
    title: document.querySelector("#rr-title-in").value,
    description: document.querySelector("#rr-desc").value,
    detour_stops: document.querySelector("#rr-detour").value,
    original_stops: document.querySelector("#rr-original").value,
    source_label: document.querySelector("#rr-source").value,
    starts_at: document.querySelector("#rr-start").value,
    ends_at: document.querySelector("#rr-end").value || null,
    until_further_notice: document.querySelector("#rr-ufn").checked,
  };
  const { data } = await api("/api/staff/reroutes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  document.querySelector("#rr-msg").textContent = data.ok
    ? `Saved as ${data.reroute.status}${data.reroute.verified ? " (Verified)" : " (needs admin)"}`
    : data.error;
  loadQueue();
});

document.querySelector("#adv-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    advisory_type: document.querySelector("#adv-type").value,
    severity: document.querySelector("#adv-sev").value,
    title: document.querySelector("#adv-title-in").value,
    description: document.querySelector("#adv-desc").value,
    affected_route_codes: document.querySelector("#adv-routes").value,
    starts_at: document.querySelector("#adv-start").value,
    ends_at: document.querySelector("#adv-end").value || null,
    source_label: document.querySelector("#adv-source")?.value || "operator",
  };
  const { data } = await api("/api/staff/advisories", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  document.querySelector("#adv-msg").textContent = data.ok
    ? `Saved as ${data.advisory.status}`
    : data.error;
  loadQueue();
});

async function loadReports() {
  const q = document.querySelector("#rep-q")?.value || "";
  const status = document.querySelector("#rep-status")?.value || "";
  const { data } = await api(
    `/api/staff/reports?q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}`
  );
  const box = document.querySelector("#report-queue");
  if (!data.ok) {
    box.textContent = data.error;
    return;
  }
  document.querySelector("#report-analytics").textContent = JSON.stringify(data.analytics, null, 2);
  box.innerHTML =
    (data.reports || [])
      .slice(0, 20)
      .map(
        (r) => `
    <div class="ri-card">
      <strong>${r.ref_code}</strong> · ${r.status}
      <p>${r.category_label} · ${r.route_code || "—"}</p>
      <p class="ri-meta">${r.description.slice(0, 120)}</p>
      <button type="button" class="trip-mini-btn" data-st="under_review:${r.id}">Under review</button>
      <button type="button" class="trip-mini-btn" data-st="approved:${r.id}">Approve</button>
      <button type="button" class="trip-mini-btn" data-st="rejected:${r.id}">Reject</button>
      <button type="button" class="trip-mini-btn" data-apply="${r.id}">Apply correction draft</button>
    </div>`
      )
      .join("") || "<p class='ri-empty'>No reports.</p>";

  box.querySelectorAll("[data-st]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const [status, id] = btn.getAttribute("data-st").split(":");
      let note = "";
      if (status === "rejected") {
        note = prompt("Reject reason (required):") || "";
        if (!note) return;
      }
      const { data: d } = await api(`/api/reports/${id}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, note }),
      });
      alert(d.ok ? d.report.notification : d.error);
      loadReports();
    });
  });
  box.querySelectorAll("[data-apply]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const { data: d } = await api(`/api/staff/reports/${btn.getAttribute("data-apply")}/apply`, {
        method: "POST",
      });
      alert(d.ok ? `Draft approval #${d.draft.approval_id}` : d.error);
      loadQueue();
    });
  });
}

document.querySelector("#rep-reload")?.addEventListener("click", loadReports);

document.querySelector("#csv-preview")?.addEventListener("click", async () => {
  const csv = document.querySelector("#csv-in").value;
  const { data } = await api("/api/staff/import/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ csv }),
  });
  document.querySelector("#csv-out").textContent = JSON.stringify(data, null, 2);
});

// Default start times
const isoNow = new Date().toISOString().slice(0, 19) + "Z";
["#adv-start", "#rr-start"].forEach((sel) => {
  const el = document.querySelector(sel);
  if (el && !el.value) el.value = isoNow;
});

loadQueue();
loadReports();
