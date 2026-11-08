import copy
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
            key=OutstandingTask.get_deadline
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


