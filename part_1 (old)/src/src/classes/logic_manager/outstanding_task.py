from datetime import datetime, date
from classes.logic_manager.task import Task

class OutstandingTask(Task):
    def __init__(self, name, description, owners, deadline):
        super().__init__(name, description, owners)
        self.__deadline = deadline

    def validate(self):
        errors = super().validate()

        if not self.__deadline or not self.__deadline.strip():
            errors.append("missing_deadline")
        elif not self.validate_deadline():
            errors.append("invalid_deadline")

        return errors

    def validate_deadline(self):
        try:
            deadline_date = datetime.strptime(self.__deadline, "%d/%m/%Y").date()
            return deadline_date >= date.today()
        except (ValueError, TypeError):
            return False

    def get_deadline(self):
        return datetime.strptime(self.__deadline, "%d/%m/%Y")

    def to_dict(self):
        data = super().to_dict()
        data["deadline"] = self.__deadline
        return data
