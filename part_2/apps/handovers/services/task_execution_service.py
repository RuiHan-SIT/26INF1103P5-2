from datetime import date
from typing import Any, Dict, List, Optional

from apps.handovers.data_manager.data_manager_error import DataManagerError
from apps.handovers.data_manager.handover_query import HandoverQuery
from apps.handovers.data_manager.handover_repository import HandoverRepository
from apps.handovers.logic_manager.outstanding_task import OutstandingTask
from apps.handovers.logic_manager.workload_validator import BAU_FREQUENCY_RULES
from apps.handovers.models import TaskCompletion


class TaskExecutionService:
    """Handles task calendar projection, BAU occurrence rules, and task/subtask status transitions."""

    def __init__(
        self,
        query: Optional[HandoverQuery] = None,
        repository: Optional[HandoverRepository] = None,
    ):
        self._query = query or HandoverQuery()
        self._repository = repository or HandoverRepository()

    def build_my_tasks_context(self, employee: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Build calendar_tasks and unscheduled_tasks lists for the employee's My Tasks view."""
        calendar_tasks: List[Dict[str, Any]] = []
        unscheduled_tasks: List[Dict[str, Any]] = []

        if not employee:
            return {
                "calendar_tasks": calendar_tasks,
                "unscheduled_tasks": unscheduled_tasks,
            }

        for task in self._query.tasks_owned_by(employee):
            handover_label = f"H-{task.handover_id:04d}"
            if task.task_type == "bau":
                calendar_tasks.append(self._serialize_bau_task(task, handover_label))
                continue

            subtasks = list(task.subtasks.all())
            has_planned_subtask = False
            for subtask in subtasks:
                if subtask.planned_date:
                    has_planned_subtask = True
                    calendar_tasks.append(
                        self._serialize_planned_subtask(task, subtask, handover_label)
                    )

            if task.deadline:
                calendar_tasks.append(
                    self._serialize_deadline_task(task, subtasks, handover_label)
                )
            elif not has_planned_subtask:
                unscheduled_tasks.append({
                    "title": task.title,
                    "handover": handover_label,
                })

        return {
            "calendar_tasks": calendar_tasks,
            "unscheduled_tasks": unscheduled_tasks,
        }

    @staticmethod
    def _serialize_bau_task(task: Any, handover_label: str) -> Dict[str, Any]:
        return {
            "id": f"task-{task.pk}",
            "taskId": task.pk,
            "title": task.title,
            "handover": handover_label,
            "type": "bau",
            "startDate": task.start_date.isoformat() if task.start_date else None,
            "endDate": task.end_date.isoformat() if task.end_date else None,
            "frequency": task.frequency,
            "completedDates": [
                item.completion_date.isoformat() for item in task.completions.all()
            ],
        }

    @staticmethod
    def _serialize_planned_subtask(
        task: Any, subtask: Any, handover_label: str
    ) -> Dict[str, Any]:
        return {
            "id": f"subtask-{subtask.pk}",
            "subtaskId": subtask.pk,
            "taskId": task.pk,
            "title": f"{subtask.code} {subtask.title}",
            "parentTaskId": task.code,
            "parentTask": task.title,
            "handover": handover_label,
            "type": "planned",
            "date": subtask.planned_date.isoformat(),
            "completed": subtask.status == "done",
            "dependencies": [f"subtask-{dep.pk}" for dep in subtask.depends_on.all()],
        }

    @staticmethod
    def _serialize_deadline_task(
        task: Any, subtasks: List[Any], handover_label: str
    ) -> Dict[str, Any]:
        return {
            "id": f"deadline-{task.pk}",
            "taskId": task.pk,
            "title": task.title,
            "handover": handover_label,
            "type": "deadline",
            "date": task.deadline.isoformat(),
            "completed": task.is_completed,
            "hasSubtasks": bool(subtasks),
            "subtasksComplete": all(subtask.status == "done" for subtask in subtasks),
            "subtaskIds": [f"subtask-{subtask.pk}" for subtask in subtasks],
        }

    @staticmethod
    def is_bau_occurrence(task: Any, occurrence_date: date) -> bool:
        """Return True when occurrence_date falls on a scheduled occurrence of the BAU task."""
        if not task.start_date or occurrence_date < task.start_date:
            return False
        if task.end_date and occurrence_date > task.end_date:
            return False

        frequency = (task.frequency or "").strip().lower()
        rule = BAU_FREQUENCY_RULES.get(frequency)
        if rule is None:
            return occurrence_date == task.start_date
        return rule(task.start_date, occurrence_date)

    def update_task_status(
        self,
        employee: Any,
        task_id: int,
        mark_done: Any,
        occurrence_date_str: str = "",
    ) -> Dict[str, Any]:
        """Update completion status for an outstanding task or a specific BAU occurrence."""
        if not employee:
            return {"success": False, "status_code": 403, "error_message": "Employee profile unavailable."}
        if not isinstance(mark_done, bool):
            return {"success": False, "status_code": 400, "error_message": "Invalid completion value."}

        try:
            task = self._query.task_with_progress(task_id, employee)
        except DataManagerError as error:
            return {"success": False, "status_code": 503, "error_message": str(error)}

        if task is None:
            return {"success": False, "status_code": 404, "error_message": "Task not found."}

        if task.task_type == "bau":
            return self._update_bau_occurrence(task, mark_done, occurrence_date_str)

        if task.task_type != "outstanding":
            return {"success": False, "status_code": 400, "error_message": "Unsupported task type."}

        if mark_done and task.subtasks.exists() and task.subtasks.exclude(status="done").exists():
            return {
                "success": False,
                "status_code": 409,
                "error_message": "Complete all subtasks before marking this task complete.",
            }

        task.is_completed = mark_done
        task.save(update_fields=["is_completed"])
        return {"success": True, "status_code": 200, "completed": mark_done}

    def _update_bau_occurrence(
        self,
        task: Any,
        mark_done: bool,
        occurrence_date_str: str,
    ) -> Dict[str, Any]:
        try:
            occurrence_date = date.fromisoformat(occurrence_date_str or "")
        except (TypeError, ValueError):
            return {"success": False, "status_code": 400, "error_message": "Invalid occurrence date."}

        if not self.is_bau_occurrence(task, occurrence_date):
            return {
                "success": False,
                "status_code": 400,
                "error_message": "That date is not a scheduled occurrence of this BAU task.",
            }

        if mark_done:
            TaskCompletion.objects.get_or_create(task=task, completion_date=occurrence_date)
        else:
            TaskCompletion.objects.filter(task=task, completion_date=occurrence_date).delete()
        return {"success": True, "status_code": 200, "completed": mark_done}

    def update_subtask_status(
        self,
        employee: Any,
        subtask_id: int,
        mark_done: Any,
    ) -> Dict[str, Any]:
        """Update completion status for a subtask while enforcing dependency order."""
        if not employee:
            return {"success": False, "status_code": 403, "error_message": "Employee profile unavailable."}
        if not isinstance(mark_done, bool):
            return {"success": False, "status_code": 400, "error_message": "Invalid completion value."}

        subtask = self._query.subtask_with_task(subtask_id)
        if subtask is None:
            return {"success": False, "status_code": 404, "error_message": "Subtask not found."}
        if not subtask.task.owners.filter(pk=employee.pk).exists():
            return {"success": False, "status_code": 403, "error_message": "You are not assigned to this task."}

        if mark_done:
            if not self._can_complete_subtask(subtask):
                return {
                    "success": False,
                    "status_code": 409,
                    "error_message": "Complete the required earlier subtask(s) first.",
                }
        elif subtask.needed_by.filter(status="done").exists():
            return {
                "success": False,
                "status_code": 409,
                "error_message": "A later dependent subtask is already complete. Undo that first.",
            }

        try:
            self._repository.update_subtask_status(subtask, mark_done)
            if not mark_done and subtask.task.is_completed:
                subtask.task.is_completed = False
                subtask.task.save(update_fields=["is_completed"])
        except DataManagerError as error:
            return {"success": False, "status_code": 503, "error_message": str(error)}

        return {"success": True, "status_code": 200, "completed": mark_done}

    @staticmethod
    def _can_complete_subtask(subtask: Any) -> bool:
        task_subtasks = list(subtask.task.subtasks.all())
        logic_subtasks = [
            {
                "subtask_id": item.code,
                "task": item.title,
                "planned_date": item.planned_date.strftime("%d/%m/%Y") if item.planned_date else "",
                "dependencies": list(item.depends_on.values_list("code", flat=True)),
            }
            for item in task_subtasks
        ]
        manager = OutstandingTask(
            name=subtask.task.title,
            description=subtask.task.description or "Task",
            owners=list(subtask.task.owners.values_list("name", flat=True)),
            owner_ids=list(subtask.task.owners.values_list("employee_id", flat=True)),
            deadline=(subtask.task.deadline or subtask.planned_date).strftime("%d/%m/%Y"),
            task_id=subtask.task_id,
            subtasks=logic_subtasks,
        )
        completed_codes = set(
            subtask.task.subtasks.filter(status="done").values_list("code", flat=True)
        )
        return manager.can_complete_subtask(subtask.code, completed_codes)
