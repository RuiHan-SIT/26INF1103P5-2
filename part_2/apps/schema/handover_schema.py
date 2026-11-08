from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class SubtaskSchema(BaseModel):
    subtask_id: Optional[str] = None
    task: str = ""
    planned_date: str = ""
    dependencies: List[str] = Field(default_factory=list)

    @field_validator("dependencies", mode="before")
    @classmethod
    def clean_dependencies(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        return [str(item).strip() for item in v if str(item).strip()]


class OutstandingTaskSchema(BaseModel):
    task_id: Optional[str] = None
    task: str = ""
    description: str = ""
    owners: List[str] = Field(default_factory=list)
    owner_ids: List[str] = Field(default_factory=list)
    deadline: str = ""
    subtasks: List[SubtaskSchema] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)

    @field_validator("owners", "clarification_questions", mode="before")
    @classmethod
    def clean_string_list(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        return [str(x).strip() for x in v if str(x).strip()]

    @field_validator("task", "description", "deadline", mode="before")
    @classmethod
    def clean_text_field(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()


class BAUTaskSchema(BaseModel):
    task_id: Optional[str] = None
    task: str = ""
    description: str = ""
    owners: List[str] = Field(default_factory=list)
    owner_ids: List[str] = Field(default_factory=list)
    frequency: str = ""
    start_date: str = ""
    end_date: Optional[str] = None
    clarification_questions: List[str] = Field(default_factory=list)

    @field_validator("frequency", mode="before")
    @classmethod
    def clean_frequency(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip().lower()

    @field_validator("end_date", mode="before")
    @classmethod
    def clean_end_date(cls, v: Any) -> Optional[str]:
        if v is None or not str(v).strip():
            return None
        return str(v).strip()

    @field_validator("owners", "clarification_questions", mode="before")
    @classmethod
    def clean_string_list(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        return [str(x).strip() for x in v if str(x).strip()]

    @field_validator("task", "description", "start_date", mode="before")
    @classmethod
    def clean_text_field(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()


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
