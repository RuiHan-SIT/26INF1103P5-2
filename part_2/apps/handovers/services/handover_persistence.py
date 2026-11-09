from datetime import datetime

from django.db import transaction

from apps.handovers.models import Handover, Subtask, Task


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%d/%m/%Y").date()


@transaction.atomic
def save_handover_records(employee, upload, processed_data):
    """Save a LogicManager-approved handover and connect it to its upload."""
    handover = Handover.objects.create(
        created_by=employee,
        important_information=processed_data["important_information"],
    )

    for index, task_data in enumerate(processed_data["outstanding_tasks"], start=1):
        task = Task.objects.create(
            handover=handover,
            code=f"OUT-{index:03d}",
            task_type="outstanding",
            title=task_data["task"],
            description=task_data["description"],
            deadline=_parse_date(task_data["deadline"]),
        )
        task.owners.set(task_data["owner_ids"])

        subtask_records = {}
        used_subtask_codes = set()
        fallback_index = 1
        for subtask_index, subtask_data in enumerate(task_data["subtasks"], start=1):
            original_id = subtask_data["subtask_id"]
            code = original_id
            if len(code) > 10 or code in used_subtask_codes:
                code = f"S{fallback_index:03d}"
                while code in used_subtask_codes:
                    fallback_index += 1
                    code = f"S{fallback_index:03d}"
                fallback_index += 1
            used_subtask_codes.add(code)
            subtask_records[original_id] = Subtask.objects.create(
                task=task,
                code=code,
                title=subtask_data["task"],
                planned_date=_parse_date(subtask_data["planned_date"]),
            )

        for subtask_data in task_data["subtasks"]:
            subtask_records[subtask_data["subtask_id"]].depends_on.set(
                [subtask_records[dependency]
                for dependency in subtask_data["dependencies"]
                ]
            )

    for index, task_data in enumerate(processed_data["bau_tasks"], start=1):
        task = Task.objects.create(
            handover=handover,
            code=f"BAU-{index:03d}",
            task_type="bau",
            title=task_data["task"],
            description=task_data["description"],
            frequency=task_data["frequency"],
            start_date=_parse_date(task_data["start_date"]),
            end_date=_parse_date(task_data["end_date"]),
        )
        task.owners.set(task_data["owner_ids"])

    upload.handover = handover
    upload.save(update_fields=["handover"])
    return handover
