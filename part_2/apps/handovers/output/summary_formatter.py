from datetime import datetime

from .constants import NOT_SPECIFIED, WIDTH


class SummaryFormatter:
    """Turns handover data into readable summary text."""

    def format(self, result, user_details=None):
        outstanding_tasks = result.get("outstanding_tasks", [])
        bau_tasks = result.get("bau_tasks", [])
        important_information = result.get("important_information", [])

        # Count both task groups for the summary header.
        total_tasks = len(outstanding_tasks) + len(bau_tasks)

        lines = self._header_lines(total_tasks, user_details)
        lines.extend(
            self._task_lines(
                "OUTSTANDING TASKS",
                outstanding_tasks,
                show_deadline=True,
            )
        )
        lines.extend(
            self._task_lines(
                "ROUTINE (BAU) TASKS",
                bau_tasks,
                show_deadline=False,
            )
        )
        lines.extend(self._information_lines(important_information))

        return "\n".join(lines).rstrip()

    def format_viewing_entry(self, name, employee_id, is_first_view):
        viewed_on = datetime.now().strftime("%d %b %Y %H:%M:%S")

        entry = (
            f"Viewed by    : {name}\n"
            f"Employee ID  : {employee_id}\n"
            f"Viewed on    : {viewed_on}\n"
        )

        if is_first_view:
            # Add the heading only for the first person who views the summary.
            return (
                "\n\n\n"
                + "=" * WIDTH
                + "\n"
                + "VIEWING HISTORY\n"
                + "=" * WIDTH
                + "\n"
                + entry
            )

        return "\n" + entry

    def _header_lines(self, total_tasks, user_details):
        lines = [
            "=" * WIDTH,
            "HANDOVER SUMMARY",
            "=" * WIDTH,
            f"Generated on  : {datetime.now():%Y-%m-%d %H:%M}",
        ]

        if user_details:
            name = self._clean(user_details.get("name"))
            employee_id = self._clean(user_details.get("employee_id"))
            lines.append(f"Employee      : {name} (ID: {employee_id})")

            department = user_details.get("department")
            if department:
                lines.append(f"Department    : {self._clean(department)}")

        lines.append(f"Tasks         : {total_tasks}")
        lines.append("")
        return lines

    def _task_lines(self, heading, tasks, show_deadline):
        if not tasks:
            return []

        lines = [heading, "-" * WIDTH]

        for number, task in enumerate(tasks, start=1):
            # Some data uses "task"; database-style data may use "title".
            title = task.get("task", task.get("title"))
            lines.append(f"Task {number}: {self._clean(title)}")
            lines.append(f"    Owner       : {self._owners_text(task.get('owners'))}")
            lines.append(
                f"    Description : {self._clean(task.get('description'))}"
            )

            if show_deadline:
                lines.append(f"    Deadline    : {self._clean(task.get('deadline'))}")
            else:
                lines.append(f"    Frequency   : {self._clean(task.get('frequency'))}")
                lines.append(f"    Start date  : {self._clean(task.get('start_date'))}")
                lines.append(f"    End date    : {self._clean(task.get('end_date'))}")

            priority = task.get("priority")
            if priority:
                lines.append(f"    Priority    : {self._clean(priority)}")

            # Subtasks are optional, so this adds nothing if they are absent
            lines.extend(self._subtask_lines(task.get("subtasks", [])))
            lines.append("")

        return lines

    def _subtask_lines(self, subtasks):
        if not subtasks:
            return []

        lines = ["    Subtasks:"]
        for number, subtask in enumerate(subtasks, start=1):
            title = subtask.get("task", subtask.get("title"))
            planned_date = self._clean(subtask.get("planned_date"))
            lines.append(
                f"      {number}. {self._clean(title)} "
                f"(planned: {planned_date})"
            )

            dependencies = subtask.get("dependencies", [])
            if dependencies:
                lines.append(
                    f"         Depends on: {self._owners_text(dependencies)}"
                )

        return lines

    def _information_lines(self, information):
        if not information:
            return []

        lines = ["IMPORTANT INFORMATION", "-" * WIDTH]
        for item in information:
            lines.append(f"* {self._clean(item)}")

        return lines

    def _owners_text(self, owners):
        # Join multiple owners into one readable line.
        if isinstance(owners, (list, tuple)):
            owners = ", ".join(str(owner) for owner in owners if owner)

        return self._clean(owners)

    def _clean(self, value):
        if value is None or str(value).strip() == "":
            return NOT_SPECIFIED

        return str(value).strip()