from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


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
