from datetime import date
from typing import Any, Dict, List, Mapping, Optional, Tuple

from apps.handovers.data_manager.handover_repository import HandoverRepository
from apps.handovers.logic_manager.employee_identity_matcher import EmployeeIdentityMatcher

TASK_TYPE_SPECS: Tuple[Dict[str, str], ...] = (
    {
        "task_type": "outstanding",
        "data_key": "outstanding_tasks",
        "section_title": "One-off tasks",
        "type_label": "One-off task",
    },
    {
        "task_type": "bau",
        "data_key": "bau_tasks",
        "section_title": "Recurring BAU tasks",
        "type_label": "Recurring BAU task",
    },
)

FIELD_ERROR_LABELS: Dict[str, Tuple[str, str]] = {
    "task": ("title", "Task name is required."),
    "description": ("description", "Description is required."),
    "missing_owner(s)": ("owners", "Each task needs an owner."),
    "missing_deadline": ("deadline", "One-off tasks need a deadline."),
    "invalid_deadline": ("deadline", "Deadline must be a valid date that is today or later."),
    "missing_frequency": ("frequency", "Choose a frequency for this BAU task."),
    "invalid_frequency": ("frequency", "Choose weekly, monthly, or yearly frequency."),
    "missing_start_date": ("start_date", "BAU task needs a start date."),
    "invalid_start_date": ("start_date", "Enter a valid BAU start date."),
    "end_date_before_start_date": ("end_date", "End date must be on or after the start date."),
    "invalid_end_date": ("end_date", "Enter a valid BAU end date."),
}

SUBTASK_ERROR_LABELS: Dict[str, Tuple[str, str]] = {
    "missing_task": ("title", "Subtask name is required."),
    "missing_planned_date": ("planned_date", "Subtask needs a planned date."),
    "invalid_planned_date": ("planned_date", "Enter a valid planned date."),
    "planned_date_after_deadline": ("planned_date", "Move this date to the parent deadline or earlier."),
    "dependency_date_order": ("planned_date", "This subtask must be dated on or after its prerequisite."),
    "invalid_dependency": ("planned_date", "Check this subtask's prerequisite order."),
    "invalid_dependencies": ("planned_date", "Check this subtask's prerequisite order."),
    "missing_id": ("title", "This subtask is missing its ID."),
    "duplicate_id": ("title", "This subtask ID is duplicated."),
    "invalid": ("title", "This subtask needs review."),
}

MATCH_LEVEL_LABELS: Dict[str, str] = {
    "exact": "Exact name match",
    "components": "Name parts match",
    "fuzzy": "Possible spelling match",
}


class HandoverDraftMapper:
    """Pure in-memory translator between AI/session dicts, LogicHandover, forms, and ORM objects."""

    parse_handover_date = staticmethod(HandoverRepository._parse_date)
    allocate_subtask_code = staticmethod(HandoverRepository.allocate_subtask_code)

    @staticmethod
    def group_tasks_by_type(tasks: List[Any]) -> Dict[str, List[Any]]:
        """Group ORM task instances by their task_type using TASK_TYPE_SPECS."""
        return {
            spec["task_type"]: [task for task in tasks if task.task_type == spec["task_type"]]
            for spec in TASK_TYPE_SPECS
        }

    def build_review_sections(
        self,
        data: Dict[str, Any],
        employees: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build UI review sections with employee match suggestions and clarification questions."""
        matcher = EmployeeIdentityMatcher(employees)
        departments = sorted({emp["department"] for emp in employees})
        sections = []

        for spec in TASK_TYPE_SPECS:
            task_type = spec["task_type"]
            reviewed_tasks = []
            for task_index, task in enumerate(data.get(spec["data_key"], [])):
                owner_reviews = self._build_owner_reviews(
                    task=task,
                    spec=spec,
                    task_index=task_index,
                    employees=employees,
                    departments=departments,
                    matcher=matcher,
                )
                clarification_questions = [
                    {
                        "question": question,
                        "field_name": f"clarification_{task_type}_{task_index}_{q_index}",
                    }
                    for q_index, question in enumerate(task.get("clarification_questions", []))
                ]
                reviewed_tasks.append({
                    "title": task.get("task", "Untitled task"),
                    "description": task.get("description", ""),
                    "owner_reviews": owner_reviews,
                    "clarification_questions": clarification_questions,
                })

            if reviewed_tasks:
                sections.append({"title": spec["section_title"], "tasks": reviewed_tasks})

        return sections

    def _build_owner_reviews(
        self,
        task: Dict[str, Any],
        spec: Dict[str, str],
        task_index: int,
        employees: List[Dict[str, Any]],
        departments: List[str],
        matcher: EmployeeIdentityMatcher,
    ) -> List[Dict[str, Any]]:
        task_type = spec["task_type"]
        owner_names = task.get("owners", []) or [""]
        owner_reviews = []

        for owner_index, owner_name in enumerate(owner_names):
            match_result = (
                matcher.match_owners([owner_name])[0]
                if owner_name
                else {"match_level": None, "matches": []}
            )
            matched_by_id = {
                match["employee_id"]: match for match in match_result["matches"]
            }

            directory_choices = []
            suggested_choices = []
            for employee in employees:
                match = matched_by_id.get(employee["employee_id"])
                choice = {
                    **employee,
                    "suggested": match is not None,
                    "similarity": match.get("similarity") if match else None,
                }
                directory_choices.append(choice)
                if match is not None:
                    suggested_choices.append(choice)

            directory_choices.sort(key=lambda choice: choice["name"].lower())
            suggested_choices.sort(key=lambda choice: choice["name"].lower())

            owner_reviews.append({
                "owner_name": owner_name or "No owner was identified",
                "task_title": task.get("task", "Untitled task"),
                "task_type_label": spec["type_label"],
                "field_name": f"owner_{task_type}_{task_index}_{owner_index}",
                "confirmation_field": f"owner_confirmed_{task_type}_{task_index}_{owner_index}",
                "match_label": MATCH_LEVEL_LABELS.get(
                    match_result["match_level"], "Choose an employee"
                ),
                "suggested_choices": suggested_choices,
                "directory_choices": directory_choices,
                "departments": departments,
            })

        return owner_reviews

    def collect_clarification_answers(
        self,
        data: Dict[str, Any],
        post_data: Mapping[str, Any],
    ) -> List[Dict[str, str]]:
        """Extract non-empty reviewer answers for task clarification questions."""
        answers = []
        for spec in TASK_TYPE_SPECS:
            task_type = spec["task_type"]
            for task_index, task in enumerate(data.get(spec["data_key"], [])):
                for q_index, question in enumerate(task.get("clarification_questions", [])):
                    field_name = f"clarification_{task_type}_{task_index}_{q_index}"
                    answer = str(post_data.get(field_name, "")).strip()
                    if answer:
                        answers.append({
                            "task": task.get("task", "Untitled task"),
                            "question": question,
                            "answer": answer,
                        })
        return answers

    def apply_owner_selections(
        self,
        data: Dict[str, Any],
        post_data: Mapping[str, Any],
        employee_records: List[Any],
    ) -> Optional[str]:
        """Validate and apply confirmed employee owner selections onto draft data."""
        employees = {emp.employee_id: emp for emp in employee_records}
        matcher = EmployeeIdentityMatcher([
            {
                "employee_id": emp.employee_id,
                "name": emp.name,
                "department": emp.department,
            }
            for emp in employee_records
        ])

        for spec in TASK_TYPE_SPECS:
            task_type = spec["task_type"]
            for task_index, task in enumerate(data.get(spec["data_key"], [])):
                owner_names = task.get("owners", []) or [""]
                selected_employees = []

                for owner_index, _ in enumerate(owner_names):
                    field_name = f"owner_{task_type}_{task_index}_{owner_index}"
                    selected_id = post_data.get(field_name, "")
                    if selected_id == "__directory__":
                        return "Choose Neither and confirm to open the employee directory."
                    if not matcher.is_registered_employee(selected_id):
                        return "Choose an employee from the registered directory."
                    employee = employees.get(selected_id)
                    if not employee:
                        return "Choose an employee for every name before saving."
                    confirmation_field = f"owner_confirmed_{task_type}_{task_index}_{owner_index}"
                    if selected_id and post_data.get(confirmation_field) != "yes":
                        return "Click Confirm for every extracted owner name before saving."
                    if employee not in selected_employees:
                        selected_employees.append(employee)

                task["owners"] = [emp.name for emp in selected_employees]
                task["owner_ids"] = [emp.employee_id for emp in selected_employees]

        return None

    def normalize_ai_subtask_codes(self, data: Dict[str, Any], tasks: List[Any]) -> None:
        """Keep AI subtask IDs unique and short enough for the database field."""
        grouped = self.group_tasks_by_type(tasks)
        for spec in TASK_TYPE_SPECS:
            for task, existing_task in zip(
                data.get(spec["data_key"], []), grouped[spec["task_type"]]
            ):
                subtasks = task.get("subtasks", [])
                id_mapping: Dict[str, str] = {}
                used_codes = set()
                next_code = 1
                existing_codes = list(
                    existing_task.subtasks.order_by("code").values_list("code", flat=True)
                )

                for subtask_index, subtask in enumerate(subtasks):
                    original_id = str(subtask.get("subtask_id") or f"AI-{next_code}")
                    candidate = (
                        existing_codes[subtask_index]
                        if subtask_index < len(existing_codes)
                        else original_id
                    )
                    code, next_code = self.allocate_subtask_code(
                        candidate, used_codes, next_code
                    )
                    id_mapping[original_id] = code
                    subtask["subtask_id"] = code
                    used_codes.add(code)

                for subtask in subtasks:
                    subtask["dependencies"] = [
                        id_mapping.get(dependency, dependency)
                        for dependency in subtask.get("dependencies", [])
                    ]

    def build_validation_attention(
        self,
        tasks: List[Any],
        validation: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Translate Logic Manager errors into highlights for the saved task fields."""
        task_groups = self.group_tasks_by_type(tasks)
        attention: Dict[str, Any] = {}
        validation_messages: List[str] = []

        for task_error in validation.get("errors", []):
            task_type = task_error.get("type")
            task_index = task_error.get("index", 0) - 1
            matching_tasks = task_groups.get(task_type, [])

            if task_index < 0 or task_index >= len(matching_tasks):
                for error_code in task_error.get("errors", []):
                    if error_code == "no_tasks":
                        validation_messages.append("At least one task is required.")
                continue

            task = matching_tasks[task_index]
            task_attention = attention.setdefault(str(task.pk), {"fields": {}, "subtasks": {}})
            subtasks = list(task.subtasks.order_by("code"))

            for error_code in task_error.get("errors", []):
                if error_code.startswith("subtask_"):
                    self._record_subtask_attention(
                        task, subtasks, task_attention, error_code, validation_messages
                    )
                    continue

                field_name, message = FIELD_ERROR_LABELS.get(
                    error_code, ("title", "Review this task's details.")
                )
                task_attention["fields"].setdefault(field_name, []).append(message)
                validation_messages.append(f"{task.title or 'Task'}: {message}")

        return attention, list(dict.fromkeys(validation_messages))

    @staticmethod
    def _record_subtask_attention(
        task: Any,
        subtasks: List[Any],
        task_attention: Dict[str, Any],
        error_code: str,
        validation_messages: List[str],
    ) -> None:
        parts = error_code.split("_")
        try:
            subtask_index = int(parts[1]) - 1
        except (ValueError, IndexError):
            subtask_index = -1

        error_name = "_".join(parts[2:])
        field_name, message = SUBTASK_ERROR_LABELS.get(
            error_name, ("planned_date", "Check this subtask's details and prerequisite order.")
        )
        if 0 <= subtask_index < len(subtasks):
            subtask = subtasks[subtask_index]
            sub_attention = task_attention["subtasks"].setdefault(str(subtask.pk), {"fields": {}})
            sub_attention["fields"].setdefault(field_name, []).append(message)
            subtask_label = subtask.code
        else:
            subtask_label = "Subtask"

        validation_messages.append(f"{task.title} · {subtask_label}: {message}")

    @staticmethod
    def attach_validation_attention(tasks: List[Any], attention: Dict[str, Any]) -> None:
        """Expose validation messages beside the corresponding edit controls."""
        for task in tasks:
            task_attention = attention.get(str(task.pk), {})
            task.attention = task_attention.get("fields", {})
            for subtask in task.subtasks.all():
                subtask_attention = task_attention.get("subtasks", {}).get(str(subtask.pk), {})
                subtask.attention = subtask_attention.get("fields", {})

    def orm_to_logic_data(self, handover: Any, tasks: List[Any]) -> Dict[str, Any]:
        """Convert saved ORM handover & task rows into the dict format expected by Logic Manager."""
        data: Dict[str, Any] = {
            "outstanding_tasks": [],
            "bau_tasks": [],
            "important_information": handover.important_information or [],
        }
        for task in tasks:
            owners = list(task.owners.all())
            record: Dict[str, Any] = {
                "task_id": task.code,
                "task": task.title,
                "description": task.description,
                "owners": [owner.name for owner in owners],
                "owner_ids": [owner.employee_id for owner in owners],
            }
            if task.task_type == "bau":
                record["frequency"] = task.frequency
                record["start_date"] = task.start_date.strftime("%d/%m/%Y") if task.start_date else ""
                record["end_date"] = task.end_date.strftime("%d/%m/%Y") if task.end_date else ""
                data["bau_tasks"].append(record)
            else:
                record["deadline"] = task.deadline.strftime("%d/%m/%Y") if task.deadline else ""
                record["subtasks"] = [
                    {
                        "subtask_id": subtask.code,
                        "task": subtask.title,
                        "planned_date": (
                            subtask.planned_date.strftime("%d/%m/%Y")
                            if subtask.planned_date
                            else ""
                        ),
                        "dependencies": [dep.code for dep in subtask.depends_on.all()],
                    }
                    for subtask in task.subtasks.all()
                ]
                data["outstanding_tasks"].append(record)
        return data

    def form_to_logic_data(
        self,
        handover: Any,
        tasks: List[Any],
        post_data: Mapping[str, Any],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Parse detail edit form POST data into Logic Manager dict format and date errors."""
        edit_errors: List[str] = []
        edit_data: Dict[str, Any] = {
            "outstanding_tasks": [],
            "bau_tasks": [],
            "important_information": handover.important_information or [],
        }

        def read_iso_date(field_name: str, label: str) -> str:
            value = str(post_data.get(field_name, "")).strip()
            if not value:
                return ""
            try:
                return date.fromisoformat(value).strftime("%d/%m/%Y")
            except ValueError:
                edit_errors.append(f"Enter a valid date for {label}.")
                return value

        for task in tasks:
            prefix = f"task_{task.pk}_"
            owners = list(task.owners.all())
            record: Dict[str, Any] = {
                "task_id": task.code,
                "task": str(post_data.get(f"{prefix}title", task.title)).strip(),
                "description": str(post_data.get(f"{prefix}description", task.description)).strip(),
                "owners": [owner.name for owner in owners],
                "owner_ids": [owner.employee_id for owner in owners],
            }
            if task.task_type == "bau":
                record["frequency"] = str(
                    post_data.get(f"{prefix}frequency", task.frequency)
                ).strip()
                record["start_date"] = read_iso_date(
                    f"{prefix}start_date", f"{task.title} start date"
                )
                record["end_date"] = read_iso_date(
                    f"{prefix}end_date", f"{task.title} end date"
                )
                edit_data["bau_tasks"].append(record)
            else:
                record["deadline"] = read_iso_date(
                    f"{prefix}deadline", f"{task.title} deadline"
                )
                record["subtasks"] = [
                    {
                        "subtask_id": subtask.code,
                        "task": str(
                            post_data.get(f"subtask_{subtask.pk}_title", subtask.title)
                        ).strip(),
                        "planned_date": read_iso_date(
                            f"subtask_{subtask.pk}_planned_date",
                            f"{task.title} subtask {subtask.code} planned date",
                        ),
                        "dependencies": list(subtask.depends_on.values_list("code", flat=True)),
                    }
                    for subtask in task.subtasks.all()
                ]
                edit_data["outstanding_tasks"].append(record)

        return edit_data, edit_errors
