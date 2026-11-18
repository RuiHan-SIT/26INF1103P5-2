from typing import Annotated, Any
from pydantic import BeforeValidator, Field, create_model


# Plain function used as a "before" validator for important_information
def normalize_important_info(items: Any) -> list[str]:
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


# pydantic model schema validation (functional API - no `class` definitions)
# Each field is defined as: name=(type, Field(...))
OutstandingTask = create_model(
    "OutstandingTask",
    task=(str, Field(description="Name or concise title of the outstanding task")),
    description=(str, Field(default="", description="Detailed summary or current progress")),
    owners=(list[str], Field(default_factory=list, description="Assigned persons or teams")),
    deadline=(str, Field(default="", description="Due date, deadline, or ETA if mentioned")),
)

BauTask = create_model(
    "BauTask",
    task=(str, Field(description="Name or summary of the routine Business as usual task")),
    description=(str, Field(default="", description="Action taken or status update")),
    owners=(list[str], Field(default_factory=list, description="Persons involved")),
)

ImportantInfoItem = create_model(
    "ImportantInfoItem",
    alert=(str, Field(description="The primary alert or notice")),
    context=(str, Field(default="", description="Supporting background or context")),
)

HandoverReport = create_model(
    "HandoverReport",
    outstanding_tasks=(list[OutstandingTask], Field(default_factory=list)),
    bau_tasks=(list[BauTask], Field(default_factory=list)),
    important_information=(
        Annotated[list[str], BeforeValidator(normalize_important_info)],
        Field(default_factory=list),
    ),
)


def validate_handover(data: dict[str, Any]) -> dict[str, Any]:
    """Validates a raw dict against the HandoverReport schema.

    Returns a plain, cleaned dict. Raises pydantic.ValidationError on mismatch.
    """
    return HandoverReport.model_validate(data).model_dump()