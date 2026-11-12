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

// Keep the row action popover tidy when the user clicks elsewhere or presses Escape.
const handoverActionMenus = document.querySelectorAll(".history-actions");
function positionHandoverMenu(menu) {
    const trigger = menu.querySelector("summary");
    const popup = menu.querySelector(".history-actions-menu");
    if (!trigger || !popup || !menu.open) return;

    const triggerBounds = trigger.getBoundingClientRect();
    const popupWidth = popup.offsetWidth;
    const popupHeight = popup.offsetHeight;
    const gap = 6;
    const margin = 8;
    const spaceBelow = window.innerHeight - triggerBounds.bottom - margin;
    const openAbove = spaceBelow < popupHeight + gap && triggerBounds.top > popupHeight + gap;
    const top = openAbove
        ? triggerBounds.top - popupHeight - gap
        : triggerBounds.bottom + gap;
    const left = Math.max(
        margin,
        Math.min(triggerBounds.right - popupWidth, window.innerWidth - popupWidth - margin)
    );

    popup.style.top = `${top}px`;
    popup.style.left = `${left}px`;
}

handoverActionMenus.forEach((menu) => {
    menu.addEventListener("toggle", () => positionHandoverMenu(menu));
});

document.addEventListener("click", (event) => {
    handoverActionMenus.forEach((menu) => {
        if (!menu.contains(event.target)) menu.open = false;
    });
});
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        handoverActionMenus.forEach((menu) => { menu.open = false; });
    }
});
document.addEventListener("scroll", () => {
    handoverActionMenus.forEach(positionHandoverMenu);
}, true);
window.addEventListener("resize", () => {
    handoverActionMenus.forEach(positionHandoverMenu);
});
