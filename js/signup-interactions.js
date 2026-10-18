document.querySelectorAll("[data-signup-form]").forEach((form) => {
  const password = form.querySelector('input[name="password"]');
  const confirmation = form.querySelector('input[name="confirm"]');
  const feedback = form.querySelector(".signup-feedback");

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

  form.querySelectorAll(".eye-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.getAttribute("aria-controls"));
      const icon = button.querySelector("i");
      const showingPassword = input.type === "password";
      input.type = showingPassword ? "text" : "password";
      button.setAttribute("aria-label", `${showingPassword ? "Hide" : "Show"} ${input.name === "confirm" ? "confirm password" : "password"}`);
      icon.classList.toggle("ri-eye-line", showingPassword);
      icon.classList.toggle("ri-eye-off-line", !showingPassword);
    });
  });

  form.querySelectorAll('input[type="file"]').forEach((input) => {
    input.addEventListener("change", () => {
      const file = input.files[0];
      const fileName = input.closest(".form-group").querySelector(".upload-name");
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

  form.querySelectorAll('input[name="vehicle-type"]').forEach((input) => {
    input.addEventListener("change", () => {
      form.querySelectorAll(".vehicle-type-card").forEach((card) => {
        card.classList.toggle("vehicle-type-card--selected", card.querySelector('input[name="vehicle-type"]').checked);
      });
    });
  });

  form.querySelectorAll('input[name="days"]').forEach((input) => {
    input.addEventListener("change", () => {
      input.closest(".weekday-chip").classList.toggle("weekday-chip--active", input.checked);
      validateOperatingDays();
    });
  });

  const operatingDays = form.querySelectorAll('input[name="days"]');
  const validateOperatingDays = () => {
    const firstDay = operatingDays[0];
    if (firstDay) {
      firstDay.setCustomValidity(
        Array.from(operatingDays).some((day) => day.checked)
          ? ""
          : "Select at least one operating day."
      );
    }
  };

  validateOperatingDays();

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    validateConfirmation();
    validateOperatingDays();
    if (!form.reportValidity()) {
      return;
    }

    const nextPage = event.submitter?.dataset.next;
    if (nextPage) {
      window.location.href = nextPage;
      return;
    }

    if (feedback) {
      feedback.textContent = "Thanks! This signup demo does not create an account or send/store your information.";
    }
  });
});
