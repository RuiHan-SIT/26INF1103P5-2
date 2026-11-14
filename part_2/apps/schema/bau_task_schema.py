from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


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
