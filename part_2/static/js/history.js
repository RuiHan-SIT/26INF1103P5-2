// Show every timestamp in the viewer's own time zone.
// The browser knows the viewer's local time zone.
document.querySelectorAll("time.local-time").forEach((el) => {
    const date = new Date(el.getAttribute("datetime"));
    if (isNaN(date)) return;   // if it can't be read, keep the UTC text
    el.textContent = date.toLocaleString("en-GB", {
        day: "2-digit", month: "short", year: "numeric",
        hour: "numeric", minute: "2-digit", hour12: true,
    });
});

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

// Apply the selected status as soon as it changes.
const historyFilterForm = document.getElementById("history-filter-form");
const statusFilter = document.getElementById("status-filter");
statusFilter.addEventListener("change", () => historyFilterForm.requestSubmit());
