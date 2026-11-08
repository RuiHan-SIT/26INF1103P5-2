from abc import ABC, abstractmethod

class Task(ABC):
    def __init__(self, name, description, owners, task_id=None, owner_ids=None):
        self.__name = name
        self.__description = description
        self.__owners = list(owners)
        self.__task_id = task_id
        if owner_ids is None:
            owner_ids = []
        self.__owner_ids = list(owner_ids)

    def get_name(self):
        return self.__name

    @abstractmethod
    def validate(self):
        errors = []

        if not self.__name.strip():
            errors.append("task")

        if not self.__description.strip():
            errors.append("description")

        if not self.__owners:
            errors.append("missing_owner(s)")

        return errors

    def to_dict(self):
        return {
            "task_id": self.__task_id,
            "task": self.__name,
            "description": self.__description,
            "owners": list(self.__owners),
            "owner_ids": list(self.__owner_ids)
        }
