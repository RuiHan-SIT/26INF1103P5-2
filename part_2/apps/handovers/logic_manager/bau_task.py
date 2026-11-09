from datetime import datetime
from .task import Task

class BAUTask(Task):
    def __init__(self, name, description, owners, frequency, start_date, end_date=None, task_id=None, owner_ids=None):
        super().__init__(name, description, owners, task_id, owner_ids)
        self.__frequency = frequency
        self.__start_date = start_date
        self.__end_date = end_date

    def validate(self):
        errors = super().validate()

        # BAU tasks need a frequency and start date; the end date is optional.
        if not self.__frequency or not self.__frequency.strip():
            errors.append("missing_frequency")
        elif self.__frequency.strip().lower() not in ["weekly", "monthly", "yearly"]:
            errors.append("invalid_frequency")

        start_date = None
        if not self.__start_date or not self.__start_date.strip():
            errors.append("missing_start_date")
        else:
            try:
                start_date = datetime.strptime(self.__start_date, "%d/%m/%Y").date()
            except (ValueError, TypeError):
                errors.append("invalid_start_date")

        if self.__end_date and self.__end_date.strip():
            try:
                end_date = datetime.strptime(self.__end_date, "%d/%m/%Y").date()
                if start_date is not None and end_date < start_date:
                    errors.append("end_date_before_start_date")
            except (ValueError, TypeError):
                errors.append("invalid_end_date")

        return errors

    def to_dict(self):
        data = super().to_dict()
        data["frequency"] = self.__frequency
        data["start_date"] = self.__start_date
        data["end_date"] = self.__end_date
        return data

