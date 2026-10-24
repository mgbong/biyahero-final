/**
 * signup-interactions.js
 *
 * Handles all signup forms:
 *   - Front-end validation (password match, file size/type, operating days)
 *   - Password show/hide toggles
 *   - API submission via fetch() to the endpoint declared in data-api=""
 *   - Redirect to data-redirect="" on success, or displays an error on failure
 *
 * For multi-step driver forms the server stores intermediate data in a
 * server-side session, so each step just POSTs its own fields.
 */

document.querySelectorAll("[data-signup-form]").forEach((form) => {
  const password    = form.querySelector('input[name="password"]');
  const confirmation = form.querySelector('input[name="confirm"]');
  const feedback    = form.querySelector(".signup-feedback");
  const apiEndpoint = form.dataset.api;       // e.g. "/api/commuter/signup"
  const redirectUrl = form.dataset.redirect;  // e.g. "/html/dashboard.html"

  // ── Password match validation ─────────────────────────────────────────────
  const validateConfirmation = () => {
    if (confirmation && password) {
      confirmation.setCustomValidity(
        confirmation.value && confirmation.value !== password.value
          ? "Passwords do not match."
          : ""
      );
    }
  };

  password?.addEventListener("input", validateConfirmation);
  confirmation?.addEventListener("input", validateConfirmation);

  // ── Show / hide password toggles ──────────────────────────────────────────
  form.querySelectorAll(".eye-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.getAttribute("aria-controls"));
      const icon  = button.querySelector("i");
      const showing = input.type === "password";
      input.type = showing ? "text" : "password";
      button.setAttribute(
        "aria-label",
        `${showing ? "Hide" : "Show"} ${input.name === "confirm" ? "confirm password" : "password"}`
      );
      icon.classList.toggle("ri-eye-line",    showing);
      icon.classList.toggle("ri-eye-off-line", !showing);
    });
  });

  // ── File upload validation ────────────────────────────────────────────────
  form.querySelectorAll('input[type="file"]').forEach((input) => {
    input.addEventListener("change", () => {
      const file     = input.files[0];
      const fileName = input.closest(".form-group")?.querySelector(".upload-name");
      let error = "";
      if (file && file.size > 10 * 1024 * 1024) {
        error = "File must be 10 MB or smaller.";
      } else if (file && !/\.(jpe?g|png|pdf)$/i.test(file.name)) {
        error = "Choose a JPG, PNG, or PDF file.";
      }
      input.setCustomValidity(error);
      if (fileName) {
        fileName.textContent = file ? file.name : "JPG, PNG or PDF · up to 10 MB";
      }
    });
  });

  // ── Vehicle type card selection ───────────────────────────────────────────
  form.querySelectorAll('input[name="vehicle-type"]').forEach((input) => {
    input.addEventListener("change", () => {
      form.querySelectorAll(".vehicle-type-card").forEach((card) => {
        card.classList.toggle(
          "vehicle-type-card--selected",
          card.querySelector('input[name="vehicle-type"]').checked
        );
      });
    });
  });

  // ── Operating days validation ─────────────────────────────────────────────
  const operatingDays = form.querySelectorAll('input[name="days"]');
  const validateOperatingDays = () => {
    const firstDay = operatingDays[0];
    if (firstDay) {
      firstDay.setCustomValidity(
        Array.from(operatingDays).some((d) => d.checked)
          ? ""
          : "Select at least one operating day."
      );
    }
  };

  operatingDays.forEach((input) => {
    input.addEventListener("change", () => {
      input.closest(".weekday-chip")?.classList.toggle("weekday-chip--active", input.checked);
      validateOperatingDays();
    });
  });

  validateOperatingDays();

  // ── Submit ────────────────────────────────────────────────────────────────
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    validateConfirmation();
    validateOperatingDays();

    if (!form.reportValidity()) return;

    // If no API endpoint is set, fall back to the old navigation behaviour
    if (!apiEndpoint) {
      const nextPage = event.submitter?.dataset.next;
      if (nextPage) {
        window.location.href = nextPage;
        return;
      }
      if (feedback) {
        feedback.textContent =
          "Thanks! This signup demo does not create an account or send/store your information.";
      }
      return;
    }

    // Disable submit button while in flight
    const submitBtn = event.submitter || form.querySelector('[type="submit"]');
    const originalLabel = submitBtn?.textContent;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Please wait…";
    }

    try {
      let res;

      // Step 3 has file uploads — must use FormData (multipart)
      if (form.enctype === "multipart/form-data" || form.querySelector('input[type="file"]')) {
        res = await fetch(apiEndpoint, {
          method: "POST",
          body:   new FormData(form),
        });
      } else {
        // Collect plain form fields as JSON
        const fields = {};
        new FormData(form).forEach((value, key) => {
          if (fields[key]) {
            // handle multi-value fields (e.g. operating days checkboxes)
            fields[key] = [].concat(fields[key], value);
          } else {
            fields[key] = value;
          }
        });
        res = await fetch(apiEndpoint, {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify(fields),
        });
      }

      const data = await res.json();

      if (data.ok) {
        if (feedback) {
          feedback.textContent = data.message || "Success!";
        }
        // Redirect after a brief moment so the user can read the message
        setTimeout(() => {
          window.location.href = redirectUrl || "/";
        }, 800);
      } else {
        if (feedback) {
          feedback.textContent = data.error || "Something went wrong. Please try again.";
          feedback.style.color = "var(--color-error, #d32f2f)";
        } else {
          alert(data.error || "Something went wrong. Please try again.");
        }
      }
    } catch (err) {
      const msg = "Could not connect to the server. Please try again.";
      if (feedback) {
        feedback.textContent = msg;
        feedback.style.color = "var(--color-error, #d32f2f)";
      } else {
        alert(msg);
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = originalLabel;
      }
    }
  });
});
