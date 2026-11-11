# summary_formatter.py
# Turns the handover result into the text of the summary.
# It only builds text: no print(), no files, no Django. So it is easy to test.

from datetime import datetime

from .constants import NOT_SPECIFIED, VIEWING_HEADING, WIDTH


class SummaryFormatter:
    """Builds the handover summary text and the "viewed by" entries."""

    # ---- public (called by OutputManager) --------------------------------
    def format(self, result, user_details=None):
        """Return the full handover summary as one string.

        result       : dict from the Logic Manager (tasks, important info)
        user_details : dict with name / employee_id / department (optional)
        """
        outstanding = result.get("outstanding_tasks", [])
        routine = result.get("bau_tasks", [])

        lines = self._header_lines(len(outstanding) + len(routine), user_details)
        lines += self._task_lines("OUTSTANDING TASKS", outstanding, is_outstanding=True)
        lines += self._task_lines("ROUTINE TASKS", routine, is_outstanding=False)
        lines += self._info_lines(result.get("important_information", []))
        return "\n".join(lines)

    def format_viewing_entry(self, name, employee_id, is_first_view):
        """Return the text added to the file each time someone opens the handover."""
        viewed_on = datetime.now().strftime("%d %b %Y %H:%M:%S")
        entry = (
            f"Viewed by    : {name}\n"
            f"Employee ID  : {employee_id}\n"
            f"Viewed on    : {viewed_on}\n"
        )
        if not is_first_view:
            return "\n" + entry
        # First viewer: add the VIEWING HISTORY heading as well
        rule = "=" * WIDTH
        return f"\n\n{rule}\n{VIEWING_HEADING}\n{rule}\n{entry}"

    # ---- private helpers --------------------------------------------------
    @staticmethod
    def _clean(value):
        """Return the value as text, or "Not specified" if it is empty."""
        if value is None or str(value).strip() == "":
            return NOT_SPECIFIED
        return str(value).strip()

    @classmethod
    def _owners_text(cls, owners):
        """Owners can be a string or a list. Return them as "A, B"."""
        if isinstance(owners, str):
            owners = [owners]
        if not owners:
            return NOT_SPECIFIED
        names = [str(o).strip() for o in owners if o and str(o).strip()]
        return ", ".join(names) if names else NOT_SPECIFIED

    def _header_lines(self, task_count, user_details):
        lines = [
            "=" * WIDTH,
            "HANDOVER SUMMARY",
            "=" * WIDTH,
            f"Generated on  : {datetime.now():%Y-%m-%d %H:%M}",
        ]
        if user_details:
            name = user_details.get("name")
            emp_id = user_details.get("employee_id")
            if name or emp_id:
                lines.append(f"Employee      : {name or 'N/A'} (ID: {emp_id or 'N/A'})")
            if user_details.get("department"):
                lines.append(f"Department    : {user_details['department']}")
        lines += [f"Tasks         : {task_count}", ""]
        return lines

    def _task_lines(self, title, tasks, is_outstanding):
        """Lines for one section. Outstanding tasks have a deadline and subtasks;
        routine (BAU) tasks have a frequency and start/end dates instead."""
        if not tasks:
            return []
        lines = [title, "-" * WIDTH]
        for number, task in enumerate(tasks, start=1):
            lines.append(f"Task {number}: {self._clean(task.get('task'))}")
            lines.append(f"    Owner       : {self._owners_text(task.get('owners'))}")
            lines.append(f"    Description : {self._clean(task.get('description'))}")
            if is_outstanding:
                lines.append(f"    Deadline    : {self._clean(task.get('deadline'))}")
                lines += self._subtask_lines(task.get("subtasks", []))
            else:
                lines.append(f"    Frequency   : {self._clean(task.get('frequency'))}")
                lines.append(f"    Start date  : {self._clean(task.get('start_date'))}")
                # end_date is optional: a routine task may have no end
                if task.get("end_date"):
                    lines.append(f"    End date    : {task['end_date']}")
            lines.append("")
        return lines

    def _subtask_lines(self, subtasks):
        """AI Stage 2 subtasks: each has a task, a planned_date and dependencies."""
        if not subtasks:
            return []
        lines = ["    Subtasks    :"]
        for sub in subtasks:
            lines.append(
                f"        - {self._clean(sub.get('task'))} "
                f"(planned: {self._clean(sub.get('planned_date'))})"
            )
            if sub.get("dependencies"):
                lines.append(f"            depends on: {', '.join(sub['dependencies'])}")
        return lines

    def _info_lines(self, items):
        if not items:
            return []
        lines = ["IMPORTANT INFORMATION", "-" * WIDTH]
        lines += [f"* {self._clean(item)}" for item in items]
        lines.append("")
        return lines