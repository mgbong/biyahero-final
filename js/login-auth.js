/**
 * login-auth.js
 * Authenticates the user against the Flask backend (/api/login)
 * and redirects to the role-appropriate dashboard on success.
 */

const loginForm     = document.querySelector("#login-form");
const loginEmail    = document.querySelector("#login-email");
const loginPassword = document.querySelector("#login-password");
const loginError    = document.querySelector("#login-error");
const submitBtn     = loginForm?.querySelector('[type="submit"]');

function setError(msg) {
  if (!loginError) return;
  loginError.textContent = msg;
  loginError.classList.add("visible");
}

function clearError() {
  if (!loginError) return;
  loginError.textContent = "";
  loginError.classList.remove("visible");
}

loginEmail?.addEventListener("input", () => {
  loginEmail.classList.remove("input-error");
  clearError();
});

loginPassword?.addEventListener("input", () => {
  loginPassword.classList.remove("input-error");
  clearError();
});

loginForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();

  const email    = loginEmail.value.trim().toLowerCase();
  const password = loginPassword.value;

  if (!email || !password) {
    setError("Please enter your email and password.");
    return;
  }

  // Disable the button while the request is in flight
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "Logging in…";
  }

  try {
    const res  = await fetch("/api/login", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (data.ok) {
      window.location.href = data.redirect;
    } else {
      loginEmail.classList.add("input-error");
      loginPassword.classList.add("input-error");
      setError(data.error || "Email address or password is incorrect.");
    }
  } catch (err) {
    setError("Could not connect to the server. Please try again.");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Log In";
    }
  }
});
