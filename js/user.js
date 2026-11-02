/**
 * user.js  —  Shared user session module
 * ========================================
 * Include this script on every authenticated page (dashboards, profile, plan-trip).
 *
 * What it does:
 *   1. Calls GET /api/me to get the live user from the server session.
 *   2. Populates .user-avatar (initials), .user-name, and greeting card name
 *      on any page that has those elements.
 *   3. Redirects to login if the server says the session is gone.
 *   4. Wires up every .btn-logout element to POST /api/logout.
 *
 * Data is also stored in sessionStorage under "biyahero_user" so other
 * scripts on the same page can read it without a second fetch.
 */

(async function () {
  // ── 1. Fetch current user ──────────────────────────────────────────────
  let user = null;

  try {
    const res = await fetch("/api/me", { credentials: "same-origin" });

    if (res.status === 401) {
      // Session expired or not logged in — send to login
      window.location.href = "/html/login.html";
      return;
    }

    const data = await res.json();
    if (!data.ok) {
      window.location.href = "/html/login.html";
      return;
    }

    user = data;
    sessionStorage.setItem("biyahero_user", JSON.stringify(user));
  } catch (_) {
    // Network error — keep static placeholder rather than bouncing user
    const stored = sessionStorage.getItem("biyahero_user");
    if (stored) {
      user = JSON.parse(stored);
    }
  }

  if (!user) return;

  // ── 2. Populate user chip (header top-right) ───────────────────────────
  const avatarEls = document.querySelectorAll(".user-avatar");
  const nameEls   = document.querySelectorAll(".user-name");

  avatarEls.forEach(el => { el.textContent = user.initials || "??"; });
  nameEls.forEach(el   => { el.textContent = user.fullname  || ""; });

  // ── 3. Populate greeting card name ────────────────────────────────────
  const firstName = (user.fullname || "").split(" ")[0];

  // Commuter greeting:  "Good morning, Maya!"
  const commuterGreeting = document.querySelector(".greeting-card__name");
  if (commuterGreeting) {
    const hour = new Date().getHours();
    const tod  = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
    commuterGreeting.textContent = `Good ${tod}, ${firstName}!`;
  }

  // Driver greeting:  "Good morning, Juan!"
  const driverGreeting = document.querySelector(".driver-greeting-card__name");
  if (driverGreeting) {
    const hour = new Date().getHours();
    const tod  = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
    driverGreeting.textContent = `Good ${tod}, ${firstName}!`;
  }

  // Operator greeting:  "Welcome, Alicia Reyes"
  const operatorGreeting = document.querySelector(".operator-greeting-card__name");
  if (operatorGreeting) {
    operatorGreeting.textContent = `Welcome, ${user.fullname}`;
  }

  // Operator profile card on dashboard
  const opProfileName = document.querySelector(".operator-profile-card strong");
  if (opProfileName) {
    opProfileName.textContent = user.fullname;
  }

  // ── 4. Expose user globally so other scripts can use it ───────────────
  window.biyaheroUser = user;

  // ── 5. Wire up logout buttons ─────────────────────────────────────────
  document.querySelectorAll(".btn-logout").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        const res  = await fetch("/api/logout", { method: "POST", credentials: "same-origin" });
        const data = await res.json();
        sessionStorage.removeItem("biyahero_user");
        window.location.href = data.redirect || "/html/login.html";
      } catch (_) {
        sessionStorage.removeItem("biyahero_user");
        window.location.href = "/html/login.html";
      }
    });
  });
})();
