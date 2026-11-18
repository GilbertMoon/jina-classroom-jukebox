const form = document.querySelector("#register-form");
const alertBox = document.querySelector("#register-alert");
const button = document.querySelector("#register-button");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  button.disabled = true;
  alertBox.className = "alert d-none";
  try {
    const response = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.querySelector("#name").value,
        email: document.querySelector("#email").value,
        password: document.querySelector("#password").value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "가입 신청에 실패했습니다.");
    alertBox.textContent = payload.message;
    alertBox.className = "alert alert-success";
    form.reset();
  } catch (error) {
    alertBox.textContent = error.message;
    alertBox.className = "alert alert-danger";
  } finally {
    button.disabled = false;
  }
});
