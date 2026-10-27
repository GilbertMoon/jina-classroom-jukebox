const form = document.querySelector("#login-form");
const alertBox = document.querySelector("#login-alert");
const submitButton = document.querySelector("#login-button");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  alertBox.classList.add("d-none");
  submitButton.disabled = true;

  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: form.email.value,
        password: form.password.value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "로그인에 실패했습니다.");
    }
    window.location.assign(payload.user.role === "ADMIN" ? "/admin" : "/docs");
  } catch (error) {
    alertBox.textContent = error.message;
    alertBox.classList.remove("d-none");
  } finally {
    submitButton.disabled = false;
  }
});
