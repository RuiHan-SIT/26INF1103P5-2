import copy
from datetime import datetime
from .outstanding_task import OutstandingTask
from .bau_task import BAUTask

TASK_CLASSES = {
    "outstanding": OutstandingTask,
    "bau": BAUTask,
}

class Handover:
    def __init__(self, data: dict) -> None:
        self.__tasks = {
            task_type: [
                cls.from_dict(task_data)
                for task_data in data.get(f"{task_type}_tasks", [])
            ]
            for task_type, cls in TASK_CLASSES.items()
        }
        self.__outstanding_tasks = self.__tasks["outstanding"]
        self.__bau_tasks = self.__tasks["bau"]
        self.__important_information = copy.deepcopy(data.get("important_information", []))

    def collect_task_errors(self, tasks: list, task_type: str) -> list:
        errors = []

        for index, task in enumerate(tasks, start=1):
            task_errors = task.validate()

            if task_errors:
                errors.append({
                    "type": task_type,
                    "index": index,
                    "task": task.get_name(),
                    "errors": task_errors
                })

        return errors

    def update_task(self, task_type: str, task_id: str, task_changes: dict) -> dict:
        task_cls = TASK_CLASSES.get(task_type)
        if not task_cls:
            return {"status": "invalid", "errors": ["invalid_task_type"]}

        tasks = self.__tasks[task_type]

        for index, current_task in enumerate(tasks):
            updated_data = current_task.to_dict()

            if updated_data.get("task_id") == task_id:
                updated_data.update(task_changes)
                if "owners" in task_changes and "owner_ids" not in task_changes:
                    # Changed owner names must be matched again before IDs stay linked.
                    updated_data["owner_ids"] = []
                updated_data["task_id"] = task_id

                # Check an edited copy before replacing the current task.
                updated_task = task_cls.from_dict(updated_data)

                errors = updated_task.validate()
                if errors:
                    return {"status": "invalid", "errors": errors}

                tasks[index] = updated_task
                return {"status": "updated", "task": updated_task.to_dict()}

        return {"status": "not_found", "errors": ["task_not_found"]}

    def validate(self) -> list:
        errors = self.collect_task_errors(
            self.__outstanding_tasks, "outstanding"
        )

        bau_errors = self.collect_task_errors(
            self.__bau_tasks, "bau"
        )

        errors.extend(bau_errors)

        if not self.__outstanding_tasks and not self.__bau_tasks:
            errors.append({
                "type": "handover",
                "errors": ["no_tasks"]
            })

        return errors

    def get_task_records(self) -> dict:
        """Returns normalized task records regardless of validation pass/fail."""
        outstanding_records = [task.to_dict() for task in self.__outstanding_tasks]
        bau_records = [task.to_dict() for task in self.__bau_tasks]
        return {
            "outstanding_tasks": outstanding_records,
            "bau_tasks": bau_records,
            "important_information": copy.deepcopy(self.__important_information),
        }

    def process(self) -> dict:
        errors = self.validate()

        # Only create the final output when every task passes validation.
        if errors:
            return {
                "status": "incomplete",
                "errors": errors
            }

        sorted_tasks = sorted(
            self.__outstanding_tasks,
            key=lambda t: t.get_deadline() or datetime.max
        )

        outstanding_records = []
        for task in sorted_tasks:
            record = task.to_dict()
            outstanding_records.append(record)

        bau_records = []
        for task in self.__bau_tasks:
            bau_records.append(task.to_dict())

        return {
            "status": "complete",
            "outstanding_tasks": outstanding_records,
            "bau_tasks": bau_records,
            "important_information": copy.deepcopy(self.__important_information)
        }


