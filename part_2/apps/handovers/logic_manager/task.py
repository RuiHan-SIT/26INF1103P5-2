from abc import ABC, abstractmethod

class Task(ABC):
    def __init__(self, name: str, description: str, owners: list, task_id: str | None = None, owner_ids: list | None = None) -> None:
        self.__name = name
        self.__description = description
        self.__owners = list(owners)
        self.__task_id = task_id
        if owner_ids is None:
            owner_ids = []
        self.__owner_ids = list(owner_ids)

    def get_name(self) -> str:
        return self.__name

    # Concrete helper checking fields shared by every task.
    def _validate_base(self) -> list:
        errors = []

        if not self.__name or not self.__name.strip():
            errors.append("task")

        if not self.__description or not self.__description.strip():
            errors.append("description")

        if not self.__owners:
            errors.append("missing_owner(s)")

        return errors

    @abstractmethod
    def validate(self) -> list:
        return self._validate_base()

    def to_dict(self) -> dict:
        return {
            "task_id": self.__task_id,
            "task": self.__name,
            "description": self.__description,
            "owners": list(self.__owners),
            "owner_ids": list(self.__owner_ids)
        }
