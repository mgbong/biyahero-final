/**
 * fare-guide.js — live fare estimates via /api/fares/estimate
 */
const fareForm = document.querySelector("#fare-form");
const fareError = document.querySelector("#fare-error");
const passengerType = document.querySelector("#passenger-type");
const fareTotal = document.querySelector("#fare-total");
const fareRouteLabel = document.querySelector("#fare-route-label");
const fareBreakdown = document.querySelector("#fare-breakdown");
const fareMeta = document.querySelector("#fare-meta");

function setError(msg) {
  if (!fareError) return;
  fareError.textContent = msg || "";
  fareError.classList.toggle("is-visible", Boolean(msg));
}

async function estimate() {
  setError("");
  const from = window.LocationPickers?.["fare-from-picker"]?.getSelected();
  const to = window.LocationPickers?.["fare-to-picker"]?.getSelected();
  if (!from?.lat || !to?.lat) {
    setError("Please choose From and To from the search list.");
    return;
  }

  const btn = document.querySelector("#fare-submit");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Calculating…";
  }

  try {
    const res = await fetch("/api/fares/estimate", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        from,
        to,
        passenger: passengerType?.value || "regular",
      }),
    });
    const data = await res.json();
    if (!data.ok) {
      setError(data.error || "Could not estimate fare.");
      return;
    }
    if (!data.found) {
      fareTotal.textContent = "—";
      fareRouteLabel.textContent = "No route found for this trip";
      fareBreakdown.innerHTML = `<ul>${(data.suggestions || [])
        .map((s) => `<li>${s}</li>`)
        .join("")}</ul>`;
      fareMeta.textContent = "";
      return;
    }

    const r = data.route;
    fareTotal.textContent = r.fare_label || "—";
    fareTotal.setAttribute(
      "aria-label",
      r.fare_summary?.aria_label || `Estimated fare ${r.fare_label}`
    );
    fareRouteLabel.textContent = `${r.mode_chain} · About ${r.duration_min} min · ${
      passengerType?.options[passengerType.selectedIndex]?.text || "Regular"
    }`;

    fareBreakdown.innerHTML = `
      <p><strong>Time:</strong> ${r.time_label || "—"}
        (ride ${r.time_breakdown?.riding_min ?? "—"} /
         walk ${r.time_breakdown?.walking_min ?? "—"} /
         wait ${r.time_breakdown?.waiting_min ?? "—"} min)</p>
      <ul>
        ${(r.legs || [])
          .map((leg) => {
            if (leg.type === "walk") {
              return `<li>Walk · ${leg.fare?.label || "Est. fare ₱0"} · ~${leg.duration_min} min</li>`;
            }
            return `<li>${leg.line_code || leg.mode} · ${leg.fare?.label || "Fare unavailable"} · ~${leg.duration_min} min</li>`;
          })
          .join("")}
      </ul>`;

    const meta = data.meta || {};
    fareMeta.textContent = `Fare data updated: ${meta.fare_updated_at || "—"}`;

    if (data.alternatives?.length > 1) {
      fareBreakdown.innerHTML += `<p class="ri-muted"><strong>Other options:</strong> ${data.alternatives
        .slice(1)
        .map((a) => `${a.mode_chain} (${a.fare_label})`)
        .join(" · ")}</p>`;
    }
  } catch {
    setError("No internet or server error. Try again.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Calculate Fare";
    }
  }
}

fareForm?.addEventListener("submit", (e) => {
  e.preventDefault();
  estimate();
});

passengerType?.addEventListener("change", () => {
  const from = window.LocationPickers?.["fare-from-picker"]?.getSelected();
  const to = window.LocationPickers?.["fare-to-picker"]?.getSelected();
  if (from && to) estimate();
});
