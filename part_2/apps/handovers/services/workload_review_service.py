import hashlib
import json
from datetime import datetime, timedelta
from django.utils import timezone
from apps.handovers.data_manager.handover_query import HandoverQuery
from apps.handovers.logic_manager.workload_validator import WorkloadValidator


class WorkloadReviewService:
    """Compare a creator's proposed schedule with each owner's existing assignments."""

    def __init__(self, query=None):
        self._query = query or HandoverQuery()
        self._validator = WorkloadValidator()

    def check(self, data: dict, exclude_handover_id: int | None = None) -> list:
        dates_by_owner = {}
        today = timezone.localdate()
        for task in data.get("outstanding_tasks", []) + data.get("bau_tasks", []):
            dates = set()
            if "frequency" in task:
                try:
                    start = datetime.strptime(task.get("start_date") or "", "%d/%m/%Y").date()
                except (ValueError, TypeError):
                    continue
                start = max(today, start)
                dates.update(self._validator.get_bau_occurrence_dates(task, start, start + timedelta(days=365)))
            else:
                for subtask in task.get("subtasks", []):
                    try:
                        dates.add(datetime.strptime(subtask.get("planned_date") or "", "%d/%m/%Y").date())
                    except (ValueError, TypeError):
                        continue
            for owner in task.get("owner_ids", []):
                dates_by_owner.setdefault(owner, set()).update(dates)
        if not any(dates_by_owner.values()):
            return []
        employees = {employee.employee_id: employee for employee in self._query.all_employees()}
        warnings = []
        for owner_id, dates in dates_by_owner.items():
            employee = employees.get(owner_id)
            if not employee:
                continue
            existing = {"outstanding_tasks": [], "bau_tasks": []}
            for task in self._query.tasks_owned_by(employee):
                if task.handover_id == exclude_handover_id:
                    continue
                record = {"task": task.title, "owner_ids": [owner_id]}
                if task.task_type == "bau":
                    record.update({"frequency": task.frequency,
                                   "start_date": task.start_date.strftime("%d/%m/%Y") if task.start_date else "",
                                   "end_date": task.end_date.strftime("%d/%m/%Y") if task.end_date else ""})
                    existing["bau_tasks"].append(record)
                else:
                    record["subtasks"] = [{"planned_date": item.planned_date.strftime("%d/%m/%Y")}
                                           for item in task.subtasks.all() if item.planned_date]
                    existing["outstanding_tasks"].append(record)
            proposed = {key: [dict(task, owner_ids=[owner_id]) for task in data.get(key, [])
                              if owner_id in task.get("owner_ids", [])]
                        for key in ["outstanding_tasks", "bau_tasks"]}
            for scheduled_date in sorted(dates):
                day = scheduled_date.strftime("%d/%m/%Y")
                for warning in self._validator.check_workload([existing, proposed], day, day):
                    warning["employee_name"] = employee.name
                    warnings.append(warning)
        return warnings

    def review_token(self, warnings: list) -> str:
        # A changed schedule/count must show its current warning before saving.
        return hashlib.sha256(json.dumps(warnings, sort_keys=True).encode()).hexdigest() if warnings else ""
