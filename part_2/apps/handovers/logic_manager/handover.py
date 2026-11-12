import copy
from datetime import datetime
from .outstanding_task import OutstandingTask
from .bau_task import BAUTask

class Handover:
    def __init__(self, data):
        self.__outstanding_tasks = []
        self.__bau_tasks = []
        self.__important_information = copy.deepcopy(data["important_information"])

        # Create task objects so each task type can validate its own fields.
        for task_data in data["outstanding_tasks"]:
            task = OutstandingTask(
                task_data["task"],
                task_data["description"],
                task_data["owners"],
                task_data["deadline"],
                task_id=task_data.get("task_id"),
                owner_ids=task_data.get("owner_ids"),
                subtasks=task_data.get("subtasks")
            )
            self.__outstanding_tasks.append(task)

        for task_data in data["bau_tasks"]:
            task = BAUTask(
                task_data["task"],
                task_data["description"],
                task_data["owners"],
                frequency=task_data.get("frequency"),
                start_date=task_data.get("start_date"),
                end_date=task_data.get("end_date"),
                task_id=task_data.get("task_id"),
                owner_ids=task_data.get("owner_ids")
            )
            self.__bau_tasks.append(task)

    def collect_task_errors(self, tasks, task_type):
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

    def update_task(self, task_type, task_id, task_changes):
        if task_type == "outstanding":
            tasks = self.__outstanding_tasks
        elif task_type == "bau":
            tasks = self.__bau_tasks
        else:
            return {"status": "invalid", "errors": ["invalid_task_type"]}

        for index, current_task in enumerate(tasks):
            updated_data = current_task.to_dict()

            if updated_data.get("task_id") == task_id:
                updated_data.update(task_changes)
                if "owners" in task_changes and "owner_ids" not in task_changes:
                    # Changed owner names must be matched again before IDs stay linked.
                    updated_data["owner_ids"] = []
                updated_data["task_id"] = task_id

                # Check an edited copy before replacing the current task.
                if task_type == "outstanding":
                    updated_task = OutstandingTask(
                        updated_data["task"],
                        updated_data["description"],
                        updated_data["owners"],
                        updated_data["deadline"],
                        task_id=updated_data.get("task_id"),
                        owner_ids=updated_data.get("owner_ids"),
                        subtasks=updated_data.get("subtasks")
                    )
                else:
                    updated_task = BAUTask(
                        updated_data["task"],
                        updated_data["description"],
                        updated_data["owners"],
                        frequency=updated_data.get("frequency"),
                        start_date=updated_data.get("start_date"),
                        end_date=updated_data.get("end_date"),
                        task_id=updated_data.get("task_id"),
                        owner_ids=updated_data.get("owner_ids")
                    )

                errors = updated_task.validate()
                if errors:
                    return {"status": "invalid", "errors": errors}

                tasks[index] = updated_task
                return {"status": "updated", "task": updated_task.to_dict()}

        return {"status": "not_found", "errors": ["task_not_found"]}

    def validate(self):
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

    def get_task_records(self):
        """Returns normalized task records regardless of validation pass/fail."""
        outstanding_records = [task.to_dict() for task in self.__outstanding_tasks]
        bau_records = [task.to_dict() for task in self.__bau_tasks]
        return {
            "outstanding_tasks": outstanding_records,
            "bau_tasks": bau_records,
            "important_information": copy.deepcopy(self.__important_information),
        }

    def process(self):
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


