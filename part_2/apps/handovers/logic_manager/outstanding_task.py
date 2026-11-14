import copy
from datetime import datetime, date
from .task import Task


class OutstandingTask(Task):
    def __init__(self, name: str, description: str, owners: list, deadline: str | None, task_id: str | None = None, owner_ids: list | None = None, subtasks: list | None = None) -> None:
        super().__init__(name, description, owners, task_id, owner_ids)
        self.__deadline = deadline
        if subtasks is None:
            subtasks = []
        self.__subtasks = copy.deepcopy(subtasks)

    @classmethod
    def from_dict(cls, data: dict) -> "OutstandingTask":
        return cls(
            name=data.get("task", data.get("name", "")),
            description=data.get("description", ""),
            owners=data.get("owners", []),
            deadline=data.get("deadline", ""),
            task_id=data.get("task_id"),
            owner_ids=data.get("owner_ids"),
            subtasks=data.get("subtasks"),
        )

    def validate(self) -> list:
        errors = self._validate_base()

        # Outstanding tasks require a valid deadline.
        if not self.__deadline or not self.__deadline.strip():
            errors.append("missing_deadline")
        elif not self.validate_deadline():
            errors.append("invalid_deadline")

        errors.extend(self.validate_subtasks())
        return errors

    def validate_deadline(self) -> list:
        try:
            deadline_date = datetime.strptime(self.__deadline, "%d/%m/%Y").date()
            return deadline_date >= date.today()
        except (ValueError, TypeError):
            return False

    def validate_subtasks(self) -> list:
        errors = []
        earlier_subtask_dates = {}

        if not isinstance(self.__subtasks, list):
            return ["invalid_subtasks"]

        try:
            deadline_date = datetime.strptime(self.__deadline, "%d/%m/%Y").date()
        except (ValueError, TypeError):
            deadline_date = None

        # Keep earlier IDs and dates to check later subtasks against them.
        for index, subtask in enumerate(self.__subtasks, start=1):
            if not isinstance(subtask, dict):
                errors.append(f"subtask_{index}_invalid")
                continue

            subtask_id = subtask.get("subtask_id")
            if not isinstance(subtask_id, str) or not subtask_id.strip():
                errors.append(f"subtask_{index}_missing_id")
                subtask_id = None
            elif subtask_id in earlier_subtask_dates:
                errors.append(f"subtask_{index}_duplicate_id")
                subtask_id = None

            subtask_name = subtask.get("task")
            if not isinstance(subtask_name, str) or not subtask_name.strip():
                errors.append(f"subtask_{index}_missing_task")

            planned_date_text = subtask.get("planned_date")
            planned_date = None
            if not isinstance(planned_date_text, str) or not planned_date_text.strip():
                errors.append(f"subtask_{index}_missing_planned_date")
            else:
                try:
                    planned_date = datetime.strptime(
                        planned_date_text, "%d/%m/%Y"
                    ).date()
                except ValueError:
                    errors.append(f"subtask_{index}_invalid_planned_date")

            if planned_date and deadline_date and planned_date > deadline_date:
                errors.append(f"subtask_{index}_planned_date_after_deadline")

            dependencies = subtask.get("dependencies")
            if not isinstance(dependencies, list):
                errors.append(f"subtask_{index}_invalid_dependencies")
            else:
                for dependency in dependencies:
                    if (
                        not isinstance(dependency, str)
                        or dependency not in earlier_subtask_dates
                    ):
                        errors.append(f"subtask_{index}_invalid_dependency")
                        break
                    elif (
                        planned_date is not None
                        and earlier_subtask_dates[dependency] is not None
                        and earlier_subtask_dates[dependency] > planned_date
                    ):
                        errors.append(f"subtask_{index}_dependency_date_order")
                        break

            if subtask_id is not None:
                earlier_subtask_dates[subtask_id] = planned_date

        return errors

    # A subtask can be completed only after all its dependencies.
    def can_complete_subtask(self, subtask_id: str, completed_subtask_ids: list) -> bool:
        for subtask in self.__subtasks:
            if not isinstance(subtask, dict):
                continue

            if subtask.get("subtask_id") == subtask_id:
                dependencies = subtask.get("dependencies")
                if not isinstance(dependencies, list):
                    return False

                for dependency in dependencies:
                    if dependency not in completed_subtask_ids:
                        return False

                return True

        return False

    def get_deadline(self) -> datetime | None:
        if not self.__deadline:
            return None
        try:
            return datetime.strptime(self.__deadline, "%d/%m/%Y")
        except (ValueError, TypeError):
            return None

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["deadline"] = self.__deadline
        data["subtasks"] = copy.deepcopy(self.__subtasks)
        return data
