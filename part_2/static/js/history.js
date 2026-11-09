// Small behaviours for the Handover History page
const profileButton = document.getElementById("profile-menu-button");
const profilePopover = document.getElementById("profile-menu");

profileButton.addEventListener("click", () => {
    const isOpen = profileButton.getAttribute("aria-expanded") === "true";
    profileButton.setAttribute("aria-expanded", String(!isOpen));
    profilePopover.hidden = isOpen;
});

// Close the menu when clicking anywhere else
document.addEventListener("click", (event) => {
    if (!profilePopover.contains(event.target) && !profileButton.contains(event.target)) {
        profilePopover.hidden = true;
        profileButton.setAttribute("aria-expanded", "false");
    }
});

// Close the menu with the Escape key
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        profilePopover.hidden = true;
        profileButton.setAttribute("aria-expanded", "false");
    }
});

const logoutAction = document.getElementById("logout-action");
const accountFeedback = document.getElementById("account-feedback");
logoutAction.addEventListener("click", () => {
    accountFeedback.textContent = "Log out will work once the login route is connected.";
    accountFeedback.hidden = false;
});