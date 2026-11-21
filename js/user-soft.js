/**
 * user-soft.js — Guest-first session helper
 * =========================================
 * Public pages work with NO account.
 * Log in / Sign up is only needed for realtime reports (and staff tools).
 * Does NOT redirect guests to login.
 */

(async function () {
  let user = null;

  try {
    const res = await fetch("/api/me", { credentials: "same-origin" });
    if (res.ok) {
      const data = await res.json();
      if (data.ok) {
        user = data;
        sessionStorage.setItem("biyahero_user", JSON.stringify(user));
      }
    } else {
      sessionStorage.removeItem("biyahero_user");
    }
  } catch (_) {
    const stored = sessionStorage.getItem("biyahero_user");
    if (stored) {
      try {
        user = JSON.parse(stored);
      } catch (_) {
        /* ignore */
      }
    }
  }

  const avatarEls = document.querySelectorAll(".user-avatar");
  const nameEls = document.querySelectorAll(".user-name");

  if (user) {
    avatarEls.forEach((el) => {
      el.textContent = user.initials || "??";
    });
    nameEls.forEach((el) => {
      el.textContent = user.fullname || "";
    });
    window.biyaheroUser = user;
  } else {
    avatarEls.forEach((el) => {
      el.textContent = "G";
    });
    nameEls.forEach((el) => {
      el.textContent = "Guest";
    });
    window.biyaheroUser = null;
  }

  // Guest: header button = Log in (optional). Logged-in: Log out.
  document.querySelectorAll(".btn-logout").forEach((btn) => {
    if (!window.biyaheroUser) {
      btn.setAttribute("aria-label", "Log in");
      btn.title = "Log in (only needed to send a report)";
      const icon = btn.querySelector("i");
      if (icon) {
        icon.className = "ri-login-box-line";
      }
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const next = encodeURIComponent(
          window.location.pathname + window.location.search
        );
        window.location.href = `/html/login.html?next=${next}`;
      });
      return;
    }

    btn.setAttribute("aria-label", "Log out");
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        const res = await fetch("/api/logout", {
          method: "POST",
          credentials: "same-origin",
        });
        const data = await res.json();
        sessionStorage.removeItem("biyahero_user");
        window.location.href = data.redirect || "/html/dashboard.html";
      } catch (_) {
        sessionStorage.removeItem("biyahero_user");
        window.location.href = "/html/dashboard.html";
      }
    });
  });
})();
