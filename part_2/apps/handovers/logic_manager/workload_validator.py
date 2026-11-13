from calendar import monthrange
from datetime import datetime, timedelta


class WorkloadValidator:
    def __init__(self, daily_limit=4):
        self.__daily_limit = daily_limit

    def check_workload(self, handovers, range_start, range_end):
        range_start = datetime.strptime(range_start, "%d/%m/%Y").date()
        range_end = datetime.strptime(range_end, "%d/%m/%Y").date()
        workload = {}

        for handover in handovers:
            for task in handover.get("outstanding_tasks", []):
                subtasks = task.get("subtasks", [])

                # Count subtasks by their planned dates instead of counting their parent too.
                for subtask in subtasks:
                    subtask_date_text = subtask.get("planned_date")
                    if not subtask_date_text:
                        continue
                    try:
                        planned_date = datetime.strptime(
                            subtask_date_text, "%d/%m/%Y"
                        ).date()
                    except (ValueError, TypeError):
                        continue
                    if range_start <= planned_date <= range_end:
                        self.add_work_item(
                            workload, task.get("owner_ids", []),
                            planned_date, task.get("task", "")
                        )

            for task in handover.get("bau_tasks", []):
                for occurrence_date in self.get_bau_occurrence_dates(
                    task, range_start, range_end
                ):
                    self.add_work_item(
                        workload, task.get("owner_ids", []),
                        occurrence_date, task.get("task", "")
                    )

        warnings = []
        for employee_id in workload:
            for scheduled_date in sorted(workload[employee_id]):
                day_workload = workload[employee_id][scheduled_date]

                if day_workload["count"] > self.__daily_limit:
                    warnings.append({
                        "type": "daily_workload_exceeded",
                        "employee_id": employee_id,
                        "date": scheduled_date.strftime("%d/%m/%Y"),
                        "count": day_workload["count"],
                        "limit": self.__daily_limit,
                        "tasks": day_workload["tasks"]
                    })

        return warnings

    def add_work_item(self, workload, owner_ids, scheduled_date, task_name):
        added_owner_ids = []

        for employee_id in owner_ids:
            if not employee_id or employee_id in added_owner_ids:
                continue
            added_owner_ids.append(employee_id)

            if employee_id not in workload:
                workload[employee_id] = {}

            if scheduled_date not in workload[employee_id]:
                workload[employee_id][scheduled_date] = {
                    "count": 0,
                    "tasks": []
                }

            workload[employee_id][scheduled_date]["count"] += 1
            workload[employee_id][scheduled_date]["tasks"].append(task_name)

    def get_bau_occurrence_dates(self, task, range_start, range_end):
        start_date_text = task.get("start_date")
        if not start_date_text:
            return []
        try:
            start_date = datetime.strptime(start_date_text, "%d/%m/%Y").date()
        except (ValueError, TypeError):
            return []

        end_date_text = task.get("end_date")
        end_date = None
        if end_date_text:
            try:
                end_date = datetime.strptime(end_date_text, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                end_date = None

        frequency = (task.get("frequency") or "").strip().lower()
        if not frequency:
            return []

        occurrence_dates = []
        current_date = range_start

        while current_date <= range_end:
            if current_date >= start_date and (end_date is None or current_date <= end_date):
                if frequency == "weekly":
                    days_since_start = (current_date - start_date).days
                    if days_since_start % 7 == 0:
                        occurrence_dates.append(current_date)
                # Use the last day when a month does not have the start day.
                elif frequency == "monthly":
                    last_day = monthrange(current_date.year, current_date.month)[1]
                    if current_date.day == min(start_date.day, last_day):
                        occurrence_dates.append(current_date)
                # The same rule handles 29 February in non-leap years.
                elif frequency == "yearly":
                    last_day = monthrange(current_date.year, start_date.month)[1]
                    if (
                        current_date.month == start_date.month
                        and current_date.day == min(start_date.day, last_day)
                    ):
                        occurrence_dates.append(current_date)

            current_date += timedelta(days=1)

        return occurrence_dates
