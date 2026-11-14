from typing import Any, Dict, List
from pydantic import BaseModel, Field, model_validator

from .bau_task_schema import BAUTaskSchema
from .outstanding_task_schema import OutstandingTaskSchema
from .subtask_schema import SubtaskSchema


class HandoverSchema(BaseModel):
    outstanding_tasks: List[OutstandingTaskSchema] = Field(default_factory=list)
    bau_tasks: List[BAUTaskSchema] = Field(default_factory=list)
    important_information: List[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_incoming_data(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return {}

        outstanding = values.get("outstanding_tasks")
        if isinstance(outstanding, list):
            for i, task in enumerate(outstanding, start=1):
                if isinstance(task, dict) and not task.get("task_id"):
                    task["task_id"] = f"OUT-{i}"

        bau = values.get("bau_tasks")
        if isinstance(bau, list):
            for i, task in enumerate(bau, start=1):
                if isinstance(task, dict) and not task.get("task_id"):
                    task["task_id"] = f"BAU-{i}"

        important_info = values.get("important_information")
        if isinstance(important_info, list):
            cleaned_info = []
            for item in important_info:
                if isinstance(item, dict):
                    vals = [str(v).strip() for v in item.values() if v]
                    cleaned_info.append(" - ".join(vals))
                elif item is not None and str(item).strip():
                    cleaned_info.append(str(item).strip())
            values["important_information"] = cleaned_info

        return values


def validate_and_normalize_handover(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a raw dictionary against HandoverSchema and returns a normalized dictionary.
    """
    return HandoverSchema.model_validate(data).model_dump()
