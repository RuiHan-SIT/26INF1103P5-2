from classes.logic_manager.task import Task


class BAUTask(Task):
    def __init__(self, name, description, owners, frequency="", start_date="", end_date="", task_id=None, owner_ids=None):
        super().__init__(name, description, owners, task_id, owner_ids)
        self.__frequency = frequency
        self.__start_date = start_date
        self.__end_date = end_date

    def validate(self):
        return super().validate()

    def to_dict(self):
        data = super().to_dict()
        data["frequency"] = self.__frequency
        data["start_date"] = self.__start_date
        data["end_date"] = self.__end_date
        return data
