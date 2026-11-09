from datetime import datetime

from .constants import NOT_SPECIFIED, WIDTH


class SummaryFormatter:
    """Builds the TEXT of the handover summary.

    It only creates text. It does not print anything and does not save files (that is the job of OutputManager and SummaryFileStore).
    """

    def format(self, result, user_details=None):
        """Return the whole handover summary as one string."""
        # .get(key, []) gives an empty list if the key is missing, so no crash
        outstanding_tasks = result.get("outstanding_tasks", [])
        routine_tasks = result.get("bau_tasks", [])
        important_info = result.get("important_information", [])

        total_tasks = len(outstanding_tasks) + len(routine_tasks)

        lines = []
        lines += self._header_lines(total_tasks, user_details)
        lines += self._task_lines("OUTSTANDING TASKS", outstanding_tasks, show_deadline=True)
        lines += self._task_lines("ROUTINE TASKS", routine_tasks, show_deadline=False)
        lines += self._info_lines(important_info)

        return "\n".join(lines)

    def format_viewing_entry(self, name, employee_id, is_first_view):
        """Return the text to add to the file when someone views a handover."""
        viewed_on = datetime.now().strftime("%d %b %Y %H:%M:%S")
        entry = (
            f"Viewed by    : {name}\n"
            f"Employee ID  : {employee_id}\n"
            f"Viewed on    : {viewed_on}\n"
        )

        if is_first_view:
            # The first viewer also gets the VIEWING HISTORY heading
            return ("\n\n\n" + "=" * WIDTH + "\n"
                    + "VIEWING HISTORY\n"
                    + "=" * WIDTH + "\n"
                    + entry)

        # Later viewers just get a blank line and their entry
        return "\n" + entry

    # ---- private helper methods (the leading _ means "only used inside this class") ----

    def _clean(self, value):
        """Turn a value into text. Use 'Not specified' if it is missing or empty."""
        if value is None or str(value).strip() == "":
            return NOT_SPECIFIED
        return str(value).strip()

    def _owners_text(self, owners):
        """Owners can be a list like ['John', 'Sam'] or a string like 'Tom'."""
        if isinstance(owners, list):
            # Join the names with commas, skipping empty ones
            owners = ", ".join(str(name).strip() for name in owners if name)
        return self._clean(owners)

    def _header_lines(self, total_tasks, user_details):
        """The top part: title, date and employee details."""
        lines = [
            "=" * WIDTH,
            "HANDOVER SUMMARY",
            "=" * WIDTH,
            f"Generated on  : {datetime.now():%Y-%m-%d %H:%M}",
        ]

        # Only show employee details if we were given them
        if user_details:
            name = user_details.get("name", "N/A")
            employee_id = user_details.get("employee_id", "N/A")
            lines.append(f"Employee      : {name} (ID: {employee_id})")
            if user_details.get("department"):
                lines.append(f"Department    : {user_details['department']}")

        lines.append(f"Tasks         : {total_tasks}")
        lines.append("")  
        return lines

    def _task_lines(self, title, tasks, show_deadline):
        """One group of tasks (outstanding or routine)."""
        if not tasks:
            return []  # no tasks, so no section at all

        lines = [title, "-" * WIDTH]

    
        for number, task in enumerate(tasks, start=1):
            lines.append(f"Task {number}: {self._clean(task.get('task'))}")
            lines.append(f"    Owner       : {self._owners_text(task.get('owners'))}")
            lines.append(f"    Description : {self._clean(task.get('description'))}")
            if show_deadline:  
                lines.append(f"    Deadline    : {self._clean(task.get('deadline'))}")
            lines.append("")
        return lines

    def _info_lines(self, important_info):
        """The important information section, shown as bullet points."""
        if not important_info:
            return []

        lines = ["IMPORTANT INFORMATION", "-" * WIDTH]
        for item in important_info:
            lines.append(f"* {self._clean(item)}")
        lines.append("")
        return lines