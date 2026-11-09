const displayedDate = new Date(2026, 10, 1);
let selectedDate = new Date(2026, 10, 18);
let calendarView = "month";
const completedTasks = new Set();

const calendarDays = document.getElementById("calendar-days");
const calendarGrid = document.querySelector(".calendar-grid");
const monthLabel = document.getElementById("month-label");
const selectedDateTitle = document.getElementById("selected-date-title");
const selectedYear = document.getElementById("selected-year");
const taskList = document.getElementById("task-list");
const taskCount = document.getElementById("task-count");

const sampleTasks = [
    {
        id: "gather-information",
        title: "1.1 Gather project information",
        handover: "H-0009",
        type: "planned",
        date: "2026-11-18"
    },
    {
        id: "analyse-information",
        title: "1.2 Analyse information",
        handover: "H-0009",
        type: "planned",
        date: "2026-11-19",
        dependencies: ["gather-information"]
    },
    {
        id: "submit-security-report",
        title: "Submit security report",
        handover: "H-0009",
        type: "deadline",
        date: "2026-11-20"
    },
    {
        id: "weekly-audit",
        title: "Weekly audit summary",
        handover: "H-0010",
        type: "bau",
        startDate: "2026-11-13",
        endDate: null
    }
];

function dateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function dateFromKey(key) {
    const [year, month, day] = key.split("-").map(Number);
    return new Date(year, month - 1, day);
}

function startOfWeek(date) {
    const firstDay = new Date(date);
    firstDay.setDate(date.getDate() - ((date.getDay() + 6) % 7));
    firstDay.setHours(0, 0, 0, 0);
    return firstDay;
}

function getTasksForDate(date) {
    const key = dateKey(date);
    return sampleTasks.filter((task) => {
        if (task.type !== "bau") {
            return task.date === key;
        }

        if (key < task.startDate || (task.endDate && key > task.endDate)) {
            return false;
        }

        const daysSinceStart = (dateFromKey(key) - dateFromKey(task.startDate)) / 86400000;
        return daysSinceStart % 7 === 0;
    });
}

function makeCalendarDay(date, visibleMonth) {
    const day = document.createElement("button");
    const key = dateKey(date);
    const tasks = getTasksForDate(date);
    const types = [...new Set(tasks.map((task) => task.type))];
    const isWeekend = date.getDay() === 0 || date.getDay() === 6;

    day.type = "button";
    day.className = "day";
    day.setAttribute("role", "gridcell");
    day.setAttribute("aria-label", date.toLocaleDateString("en-SG", {
        weekday: "long", day: "numeric", month: "long", year: "numeric"
    }));
    day.setAttribute("aria-pressed", String(key === dateKey(selectedDate)));
    day.dataset.date = key;

    if (date.getMonth() !== visibleMonth) day.classList.add("outside");
    if (isWeekend) day.classList.add("weekend");
    if (key === dateKey(selectedDate)) day.classList.add("selected");

    const number = document.createElement("span");
    number.textContent = date.getDate();
    day.appendChild(number);

    if (types.length > 0) {
        const marker = document.createElement("span");
        marker.className = "day-markers";
        marker.setAttribute("aria-hidden", "true");
        types.forEach((type) => {
            const dot = document.createElement("i");
            dot.className = `day-marker ${type}`;
            marker.appendChild(dot);
        });
        day.appendChild(marker);
    }

    day.addEventListener("click", () => {
        selectedDate = new Date(date);
        displayedDate.setFullYear(date.getFullYear(), date.getMonth(), 1);
        renderCalendar();
    });
    return day;
}

function renderCalendar() {
    const year = displayedDate.getFullYear();
    const month = displayedDate.getMonth();
    calendarDays.replaceChildren();

    if (calendarView === "month") {
        monthLabel.innerHTML = `${displayedDate.toLocaleDateString("en", { month: "long" })} <span>${year}</span>`;
        calendarGrid.setAttribute("aria-label", `${displayedDate.toLocaleDateString("en", { month: "long" })} ${year}`);
        const firstDay = new Date(year, month, 1);
        const gridStart = new Date(year, month, 1 - ((firstDay.getDay() + 6) % 7));
        for (let index = 0; index < 42; index += 1) {
            const dayDate = new Date(gridStart);
            dayDate.setDate(gridStart.getDate() + index);
            calendarDays.appendChild(makeCalendarDay(dayDate, month));
        }
        calendarGrid.classList.remove("week-view");
    } else {
        const weekStart = startOfWeek(selectedDate);
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekStart.getDate() + 6);
        monthLabel.textContent = weekStart.getMonth() === weekEnd.getMonth()
            ? `${weekStart.toLocaleDateString("en", { month: "short", day: "numeric" })}–${weekEnd.toLocaleDateString("en", { day: "numeric" })}, ${year}`
            : `${weekStart.toLocaleDateString("en", { month: "short", day: "numeric" })}–${weekEnd.toLocaleDateString("en", { month: "short", day: "numeric" })}, ${year}`;
        calendarGrid.setAttribute("aria-label", "Selected week");
        for (let index = 0; index < 7; index += 1) {
            const dayDate = new Date(weekStart);
            dayDate.setDate(weekStart.getDate() + index);
            calendarDays.appendChild(makeCalendarDay(dayDate, selectedDate.getMonth()));
        }
        calendarGrid.classList.add("week-view");
    }

    renderSelectedDay();
}

function renderSelectedDay() {
    selectedDateTitle.textContent = selectedDate.toLocaleDateString("en", {
        weekday: "long", day: "numeric", month: "short"
    });
    selectedYear.textContent = selectedDate.getFullYear();
    const tasks = getTasksForDate(selectedDate);
    taskCount.textContent = `${tasks.length} ${tasks.length === 1 ? "task" : "tasks"}`;
    taskList.replaceChildren();

    if (tasks.length === 0) {
        const empty = document.createElement("p");
        empty.className = "empty-tasks";
        empty.textContent = "No tasks scheduled for this day.";
        taskList.appendChild(empty);
        return;
    }

    tasks.forEach((task) => {
        const item = document.createElement("article");
        item.className = "task-item";
        if (completedTasks.has(task.id)) item.classList.add("completed");

        const label = document.createElement("label");
        label.className = "task-check";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = completedTasks.has(task.id);
        const dependenciesComplete = !task.dependencies || task.dependencies.every((dependency) => completedTasks.has(dependency));
        checkbox.disabled = !dependenciesComplete;
        checkbox.title = dependenciesComplete ? "" : "Complete the earlier subtask first.";
        checkbox.setAttribute("aria-label", `Mark ${task.title} complete`);
        const checkmark = document.createElement("span");
        label.append(checkbox, checkmark);
        checkbox.addEventListener("change", () => {
            if (checkbox.checked) completedTasks.add(task.id);
            else completedTasks.delete(task.id);
            item.classList.toggle("completed", checkbox.checked);
        });

        const copy = document.createElement("div");
        copy.className = "task-copy";
        const title = document.createElement("h3");
        title.textContent = task.title;
        const source = document.createElement("p");
        source.textContent = `From handover ${task.handover}`;
        copy.append(title, source);
        if (!dependenciesComplete) {
            const dependencyNote = document.createElement("small");
            dependencyNote.className = "dependency-note";
            dependencyNote.textContent = "Complete 1.1 Gather project information first.";
            copy.appendChild(dependencyNote);
        }

        const tag = document.createElement("span");
        tag.className = `task-tag ${task.type}-tag`;
        tag.textContent = task.type === "bau" ? "BAU" : task.type === "deadline" ? "Deadline" : "Planned";
        item.append(label, copy, tag);
        taskList.appendChild(item);
    });
}

function moveCalendar(amount) {
    if (calendarView === "month") {
        const originalDay = selectedDate.getDate();
        displayedDate.setMonth(displayedDate.getMonth() + amount);
        const lastDay = new Date(displayedDate.getFullYear(), displayedDate.getMonth() + 1, 0).getDate();
        selectedDate = new Date(displayedDate.getFullYear(), displayedDate.getMonth(), Math.min(originalDay, lastDay));
    } else {
        selectedDate.setDate(selectedDate.getDate() + amount * 7);
        displayedDate.setFullYear(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
    }
    renderCalendar();
}

document.getElementById("prev-period").addEventListener("click", () => moveCalendar(-1));
document.getElementById("next-period").addEventListener("click", () => moveCalendar(1));
document.getElementById("today-button").addEventListener("click", () => {
    selectedDate = new Date();
    displayedDate.setFullYear(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
    renderCalendar();
});
const viewButton = document.getElementById("calendar-view-button");
const viewMenu = document.getElementById("calendar-view-menu");
const viewLabel = document.getElementById("calendar-view-label");
const viewOptions = document.querySelectorAll(".view-option");

viewButton.addEventListener("click", () => {
    const isOpen = viewButton.getAttribute("aria-expanded") === "true";
    viewButton.setAttribute("aria-expanded", String(!isOpen));
    viewMenu.hidden = isOpen;
});

viewOptions.forEach((option) => {
    option.addEventListener("click", () => {
        calendarView = option.dataset.view;
        viewLabel.textContent = option.textContent;
        viewOptions.forEach((viewOption) => {
            const isSelected = viewOption === option;
            viewOption.classList.toggle("active", isSelected);
            viewOption.setAttribute("aria-checked", String(isSelected));
        });
        viewMenu.hidden = true;
        viewButton.setAttribute("aria-expanded", "false");
        renderCalendar();
    });
});

document.addEventListener("click", (event) => {
    if (!viewMenu.contains(event.target) && !viewButton.contains(event.target)) {
        viewMenu.hidden = true;
        viewButton.setAttribute("aria-expanded", "false");
    }
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        viewMenu.hidden = true;
        viewButton.setAttribute("aria-expanded", "false");
        viewButton.focus();
    }
});

const profileButton = document.getElementById("profile-menu-button");
const profilePopover = document.getElementById("profile-menu");
profileButton.addEventListener("click", () => {
    const isOpen = profileButton.getAttribute("aria-expanded") === "true";
    profileButton.setAttribute("aria-expanded", String(!isOpen));
    profilePopover.hidden = isOpen;
});
document.addEventListener("click", (event) => {
    if (!profilePopover.contains(event.target) && !profileButton.contains(event.target)) {
        profilePopover.hidden = true;
        profileButton.setAttribute("aria-expanded", "false");
    }
});
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

renderCalendar();
