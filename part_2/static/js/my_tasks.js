const displayedDate = new Date();
let selectedDate = new Date();
displayedDate.setDate(1);
const completedTasks = new Set();
const calendarTasksElement = document.getElementById("calendar-tasks-data");
const calendarTasks = calendarTasksElement ? JSON.parse(calendarTasksElement.textContent) : [];

calendarTasks.forEach((task) => {
    if (task.completed) completedTasks.add(task.id);
});

const calendarDays = document.getElementById("calendar-days");
const calendarWeekdays = document.getElementById("calendar-weekdays");
const calendarGrid = document.querySelector(".calendar-grid");
const monthLabel = document.getElementById("month-label");
const selectedDateTitle = document.getElementById("selected-date-title");
const selectedYear = document.getElementById("selected-year");
const taskList = document.getElementById("task-list");
const taskCount = document.getElementById("task-count");

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
    firstDay.setDate(date.getDate() - date.getDay());
    firstDay.setHours(0, 0, 0, 0);
    return firstDay;
}

function renderWeekdayHeadings(startDate, numberOfDays) {
    calendarWeekdays.replaceChildren();
    for (let index = 0; index < numberOfDays; index += 1) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + index);
        const heading = document.createElement("div");
        heading.className = "weekday";
        if (date.getDay() === 0 || date.getDay() === 6) heading.classList.add("weekend");
        heading.setAttribute("role", "columnheader");
        heading.textContent = date.toLocaleDateString("en", { weekday: "short" });
        calendarWeekdays.appendChild(heading);
    }
}

function isBauScheduled(task, key) {
    if (!task.startDate || key < task.startDate || (task.endDate && key > task.endDate)) return false;
    const date = dateFromKey(key);
    const start = dateFromKey(task.startDate);
    if (task.frequency === "weekly") return Math.floor((date - start) / 86400000) % 7 === 0;
    if (task.frequency === "monthly") return date.getDate() === start.getDate();
    if (task.frequency === "yearly") return date.getMonth() === start.getMonth() && date.getDate() === start.getDate();
    return key === task.startDate;
}

function getTasksForDate(date) {
    const key = dateKey(date);
    return calendarTasks.filter((task) => task.type === "bau"
        ? isBauScheduled(task, key)
        : task.date === key).map((task) => {
            if (task.type !== "bau") return task;
            return {
                ...task,
                id: `${task.id}-${key}`,
                occurrenceDate: key,
                completed: (task.completedDates || []).includes(key),
            };
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
    monthLabel.innerHTML = `${displayedDate.toLocaleDateString("en", { month: "long" })} <span>${year}</span>`;
    calendarGrid.setAttribute("aria-label", `${displayedDate.toLocaleDateString("en", { month: "long" })} ${year}`);
    const firstDay = new Date(year, month, 1);
    const gridStart = new Date(year, month, 1 - firstDay.getDay());
    renderWeekdayHeadings(gridStart, 7);
    for (let index = 0; index < 42; index += 1) {
        const dayDate = new Date(gridStart);
        dayDate.setDate(gridStart.getDate() + index);
        calendarDays.appendChild(makeCalendarDay(dayDate, month));
    }
    renderSelectedDay();
}

async function saveCompletion(task, completed, checkbox) {
    checkbox.disabled = true;
    try {
        const isSubtask = task.type === "planned";
        const url = isSubtask
            ? `/my-tasks/subtasks/${task.subtaskId}/status/`
            : `/my-tasks/tasks/${task.taskId}/status/`;
        const payload = { completed };
        if (task.type === "bau") payload.date = task.occurrenceDate;

        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "Could not save task progress.");

        task.completed = result.completed;
        if (task.type === "planned") {
            if (completed) completedTasks.add(task.id);
            else completedTasks.delete(task.id);
            if (!completed) {
                calendarTasks.filter((item) => item.type === "deadline" && item.taskId === task.taskId)
                    .forEach((parentTask) => { parentTask.completed = false; });
            }
            calendarTasks.filter((item) => item.type === "deadline" && item.taskId === task.taskId)
                .forEach((parentTask) => {
                    parentTask.subtasksComplete = parentTask.subtaskIds.every((id) => completedTasks.has(id));
                });
        } else if (task.type === "bau") {
            const savedTask = calendarTasks.find((item) => item.taskId === task.taskId);
            const dates = savedTask.completedDates || [];
            savedTask.completedDates = completed
                ? [...new Set([...dates, task.occurrenceDate])]
                : dates.filter((item) => item !== task.occurrenceDate);
        }
        renderSelectedDay();
    } catch (error) {
        checkbox.checked = !completed;
        window.alert(error.message);
        checkbox.disabled = false;
    }
}

function getCookie(name) {
    const cookie = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(`${name}=`));
    return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : "";
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
        if (task.completed || completedTasks.has(task.id)) item.classList.add("completed");

        const label = document.createElement("label");
        label.className = "task-check";
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = task.type === "planned" ? completedTasks.has(task.id) : Boolean(task.completed);
        const dependenciesComplete = !task.dependencies || task.dependencies.every((dependency) => completedTasks.has(dependency));
        const canMarkDone = task.type === "planned" && !checkbox.checked;
        const deadlineNeedsSubtasks = task.type === "deadline" && task.hasSubtasks && !task.subtasksComplete;
        checkbox.disabled = (canMarkDone && !dependenciesComplete)
            || (deadlineNeedsSubtasks && !checkbox.checked);
        checkbox.title = canMarkDone && !dependenciesComplete
            ? "Complete the required earlier subtask first."
            : deadlineNeedsSubtasks && !checkbox.checked
                ? "Complete all subtasks before marking this task complete."
                : "";
        checkbox.setAttribute("aria-label", `Mark ${task.title} complete`);
        const checkmark = document.createElement("span");
        label.append(checkbox, checkmark);
        checkbox.addEventListener("change", () => saveCompletion(task, checkbox.checked, checkbox));

        const copy = document.createElement("div");
        copy.className = "task-copy";
        const title = document.createElement("h3");
        title.textContent = task.title;
        copy.appendChild(title);
        if (task.parentTask) {
            const parent = document.createElement("p");
            parent.className = "task-parent";
            parent.textContent = `For ${task.parentTaskId}: ${task.parentTask}`;
            copy.appendChild(parent);
        }
        const source = document.createElement("p");
        source.textContent = `From handover ${task.handover}`;
        copy.appendChild(source);
        if (task.dependencies?.length && !dependenciesComplete) {
            const dependencyNote = document.createElement("small");
            dependencyNote.className = "dependency-note";
            dependencyNote.textContent = "Complete the required earlier subtask first.";
            copy.appendChild(dependencyNote);
        }

        const tag = document.createElement("span");
        tag.className = `task-tag ${task.type}-tag`;
        tag.textContent = task.type === "bau" ? "BAU" : task.type === "deadline" ? "Deadline" : task.type === "planned" ? "Subtask" : "Completed";
        item.append(label, copy, tag);
        taskList.appendChild(item);
    });
}

function moveCalendar(amount) {
    const originalDay = selectedDate.getDate();
    displayedDate.setMonth(displayedDate.getMonth() + amount);
    const lastDay = new Date(displayedDate.getFullYear(), displayedDate.getMonth() + 1, 0).getDate();
    selectedDate = new Date(displayedDate.getFullYear(), displayedDate.getMonth(), Math.min(originalDay, lastDay));
    renderCalendar();
}

document.getElementById("prev-period").addEventListener("click", () => moveCalendar(-1));
document.getElementById("next-period").addEventListener("click", () => moveCalendar(1));
document.getElementById("today-button").addEventListener("click", () => {
    selectedDate = new Date();
    displayedDate.setFullYear(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
    renderCalendar();
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

renderCalendar();
