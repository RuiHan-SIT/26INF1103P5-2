from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator

from .subtask_schema import SubtaskSchema


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
