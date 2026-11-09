from abc import ABC, abstractmethod

class Task(ABC):
    def __init__(self, name, description, owners):
        self.__name = name
        self.__description = description
        self.__owners = list(owners)

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
            "task": self.__name,
            "description": self.__description,
            "owners": list(self.__owners)
        }
