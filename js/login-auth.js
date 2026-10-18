const demoAccounts = {
  "commuter@biyahero.com": {
    password: "commuter123",
    dashboard: "dashboard.html",
  },
  "driver@biyahero.com": {
    password: "driver123",
    dashboard: "driver-dashboard.html",
  },
  "operator@biyahero.com": {
    password: "operator123",
    dashboard: "operator-dashboard.html",
  },
};

const loginForm = document.querySelector("#login-form");
const loginEmail = document.querySelector("#login-email");
const loginPassword = document.querySelector("#login-password");
const loginError = document.querySelector("#login-error");

loginForm.addEventListener("submit", (event) => {
  event.preventDefault();

  const email = loginEmail.value.trim().toLowerCase();
  const account = demoAccounts[email];

  if (!account || account.password !== loginPassword.value) {
    loginError.textContent = "Email address or password is incorrect.";
    loginError.classList.add("visible");
    loginEmail.classList.toggle("input-error", !account);
    loginPassword.classList.toggle("input-error", !account || account.password !== loginPassword.value);
    return;
  }

  window.location.href = account.dashboard;
});

loginEmail.addEventListener("input", () => {
  loginEmail.classList.remove("input-error");
  loginError.classList.remove("visible");
});

loginPassword.addEventListener("input", () => {
  loginPassword.classList.remove("input-error");
  loginError.classList.remove("visible");
});
