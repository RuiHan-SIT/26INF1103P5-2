const passwordInput = document.getElementById("id_password");
const passwordToggle = document.getElementById("togglePassword");

if (passwordInput && passwordToggle) {
    passwordToggle.addEventListener("click", function () {
        const showPassword = passwordInput.type === "password";
        passwordInput.type = showPassword ? "text" : "password";
        passwordToggle.dataset.visible = String(showPassword);
        passwordToggle.setAttribute("aria-pressed", String(showPassword));
        passwordToggle.setAttribute("aria-label", showPassword ? "Hide password" : "Show password");
    });
}