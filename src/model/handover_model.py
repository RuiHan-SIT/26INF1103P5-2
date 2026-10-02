from typing import Any
from pydantic import BaseModel, Field, field_validator

#pydantic model schema validation
class OutstandingTask(BaseModel):
    task: str = Field(description="Name or concise title of the outstanding task")
    description: str = Field(default="", description="Detailed summary or current progress")
    owners: list[str] = Field(default_factory=list, description="Assigned persons or teams")
    deadline: str = Field(default="", description="Due date, deadline, or ETA if mentioned")

class BauTask(BaseModel):
    task: str = Field(description="Name or summary of the routine Business as usual task")
    description: str = Field(default="", description="Action taken or status update")
    owners: list[str] = Field(default_factory=list, description="Persons involved")

class ImportantInfoItem(BaseModel):
    alert: str = Field(description="The primary alert or notice")
    context: str = Field(default="", description="Supporting background or context")

class HandoverReport(BaseModel):
    outstanding_tasks: list[OutstandingTask] = Field(default_factory=list)
    bau_tasks: list[BauTask] = Field(default_factory=list)
    important_information: list[str] = Field(default_factory=list)

    @field_validator("important_information", mode="before")
    @classmethod
    def normalize_important_info(cls, items: Any) -> list[str]:
        """Ensures important_information is always a list of strings.
        
        If the model generates [{'alert': '...', 'context': '...'}],
        this flattens it into: '... - ...'
        """
        if not isinstance(items, list):
            return []

        cleaned: list[str] = []
        for item in items:
            if isinstance(item, dict):
                # Join values like alert and context into one readable string
                vals = [str(v).strip() for v in item.values() if v]
                cleaned.append(" - ".join(vals))
            elif isinstance(item, str):
                cleaned.append(item.strip())
            else:
                cleaned.append(str(item))
        return cleaned