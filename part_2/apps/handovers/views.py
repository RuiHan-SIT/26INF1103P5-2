import json
import logging
from datetime import date, datetime
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import FileResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .data_manager.handover_repository import HandoverRepository
from .forms import HandoverUploadForm
from .logic_manager.employee_identity_matcher import EmployeeIdentityMatcher
from .logic_manager.handover import Handover as LogicHandover
from .logic_manager.outstanding_task import OutstandingTask
from .data_manager.data_manager_error import DataManagerError
from .data_manager.handover_query import HandoverQuery
from .models import Employee, Handover, Subtask, TaskCompletion
from .output.word_document_generator import CompletedHandoverDocumentGenerator
from .input_handler.handover_input_handler import HandoverInputHandler
from .services.handover_coordinator import HandoverCoordinator

logger = logging.getLogger(__name__)


PENDING_UPLOAD_KEY = "pending_handover_upload_id"
PENDING_DATA_KEY = "pending_handover_data"
CANCEL_REQUEST_TIMEOUT = 60 * 15


def handover_cancel_key(employee, request_token):
    return f"handover-cancel:{employee.pk}:{request_token}"


def valid_request_token(value):
    try:
        UUID(value)
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def handover_cancelled(employee, request_token):
    return bool(
        employee
        and valid_request_token(request_token)
        and cache.get(handover_cancel_key(employee, request_token))
    )


def clear_pending_handover(request, upload=None):
    if upload:
        HandoverRepository().delete_upload(upload)
    request.session.pop(PENDING_UPLOAD_KEY, None)
    request.session.pop(PENDING_DATA_KEY, None)


def build_review_sections(data):
    employees = HandoverQuery().employee_list()
    matcher = EmployeeIdentityMatcher(employees)
    sections = []

    for task_type, data_key, section_title in [
        ("outstanding", "outstanding_tasks", "One-off tasks"),
        ("bau", "bau_tasks", "Recurring BAU tasks"),
    ]:
        reviewed_tasks = []
        for task_index, task in enumerate(data.get(data_key, [])):
            owner_names = task.get("owners", []) or [""]
            owner_reviews = []

            for owner_index, owner_name in enumerate(owner_names):
                match_result = (
                    matcher.match_owners([owner_name])[0]
                    if owner_name else {"match_level": None, "matches": []}
                )

                matched_by_id = {
                    match["employee_id"]: match
                    for match in match_result["matches"]
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

                level_labels = {
                    "exact": "Exact name match",
                    "components": "Name parts match",
                    "fuzzy": "Possible spelling match",
                }
                owner_reviews.append({
                    "owner_name": owner_name or "No owner was identified",
                    "task_title": task.get("task", "Untitled task"),
                    "task_type_label": "One-off task" if task_type == "outstanding" else "Recurring BAU task",
                    "field_name": f"owner_{task_type}_{task_index}_{owner_index}",
                    "confirmation_field": f"owner_confirmed_{task_type}_{task_index}_{owner_index}",
                    "match_label": level_labels.get(match_result["match_level"], "Choose an employee"),
                    "suggested_choices": suggested_choices,
                    "directory_choices": directory_choices,
                    "departments": sorted({employee["department"] for employee in employees}),
                })

            clarification_questions = []
            for question_index, question in enumerate(task.get("clarification_questions", [])):
                clarification_questions.append({
                    "question": question,
                    "field_name": f"clarification_{task_type}_{task_index}_{question_index}",
                })

            reviewed_tasks.append({
                "title": task.get("task", "Untitled task"),
                "description": task.get("description", ""),
                "owner_reviews": owner_reviews,
                "clarification_questions": clarification_questions,
            })

        if reviewed_tasks:
            sections.append({"title": section_title, "tasks": reviewed_tasks})

    return sections


def collect_clarification_answers(data, post_data):
    answers = []
    for task_type, data_key in [
        ("outstanding", "outstanding_tasks"),
        ("bau", "bau_tasks"),
    ]:
        for task_index, task in enumerate(data.get(data_key, [])):
            questions = task.get("clarification_questions", [])
            for question_index, question in enumerate(questions):
                answer = post_data.get(
                    f"clarification_{task_type}_{task_index}_{question_index}", ""
                ).strip()
                if answer:
                    answers.append({
                        "task": task.get("task", "Untitled task"),
                        "question": question,
                        "answer": answer,
                    })
    return answers


def apply_owner_selections(data, post_data):
    employee_records = HandoverQuery().all_employees()
    employees = {employee.employee_id: employee for employee in employee_records}
    matcher = EmployeeIdentityMatcher([
        {
            "employee_id": employee.employee_id,
            "name": employee.name,
            "department": employee.department,
        }
        for employee in employee_records
    ])

    for task_type, data_key in [
        ("outstanding", "outstanding_tasks"),
        ("bau", "bau_tasks"),
    ]:
        for task_index, task in enumerate(data.get(data_key, [])):
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
                if selected_id and post_data.get(
                    f"owner_confirmed_{task_type}_{task_index}_{owner_index}"
                ) != "yes":
                    return "Click Confirm for every extracted owner name before saving."
                if employee not in selected_employees:
                    selected_employees.append(employee)

            task["owners"] = [employee.name for employee in selected_employees]
            task["owner_ids"] = [employee.employee_id for employee in selected_employees]

    return None


def normalize_ai_subtask_codes(data, tasks):
    """Keep AI subtask IDs unique and short enough for the database field."""
    task_groups = {
        "outstanding_tasks": [task for task in tasks if task.task_type == "outstanding"],
        "bau_tasks": [task for task in tasks if task.task_type == "bau"],
    }
    for task_type, existing_tasks in task_groups.items():
        for task, existing_task in zip(data.get(task_type, []), existing_tasks):
            subtasks = task.get("subtasks", [])
            id_mapping = {}
            used_codes = set()
            next_code = 1
            existing_codes = list(
                existing_task.subtasks.order_by("code").values_list("code", flat=True)
            )

            for subtask_index, subtask in enumerate(subtasks):
                original_id = str(subtask.get("subtask_id") or f"AI-{next_code}")
                code = existing_codes[subtask_index] if subtask_index < len(existing_codes) else original_id
                if len(code) > 10 or code in used_codes:
                    code = f"S{next_code:03d}"
                    while code in used_codes:
                        next_code += 1
                        code = f"S{next_code:03d}"
                id_mapping[original_id] = code
                subtask["subtask_id"] = code
                used_codes.add(code)
                next_code += 1

            for subtask in subtasks:
                subtask["dependencies"] = [
                    id_mapping.get(dependency, dependency)
                    for dependency in subtask.get("dependencies", [])
                ]


def _build_validation_attention(tasks, validation):
    """Translate Logic Manager errors into highlights for the saved task fields."""
    field_labels = {
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
    subtask_errors = {
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
    task_groups = {
        "outstanding": [task for task in tasks if task.task_type == "outstanding"],
        "bau": [task for task in tasks if task.task_type == "bau"],
    }
    attention = {}
    validation_messages = []

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
                parts = error_code.split("_")
                try:
                    subtask_index = int(parts[1]) - 1
                except (ValueError, IndexError):
                    subtask_index = -1
                error_name = "_".join(parts[2:])
                field_name, message = subtask_errors.get(
                    error_name, ("planned_date", "Check this subtask's details and prerequisite order.")
                )
                if 0 <= subtask_index < len(subtasks):
                    subtask = subtasks[subtask_index]
                    sub_attention = task_attention["subtasks"].setdefault(
                        str(subtask.pk), {"fields": {}}
                    )
                    sub_attention["fields"].setdefault(field_name, []).append(message)
                validation_messages.append(f"{task.title} · {subtasks[subtask_index].code if 0 <= subtask_index < len(subtasks) else 'Subtask'}: {message}")
                continue

            field_name, message = field_labels.get(
                error_code, ("title", "Review this task's details.")
            )
            task_attention["fields"].setdefault(field_name, []).append(message)
            validation_messages.append(f"{task.title or 'Task'}: {message}")

    validation_messages = list(dict.fromkeys(validation_messages))
    return attention, validation_messages


def persist_clarification_edits(request, handover, tasks, data, finalize=True):
    """Update saved rows, validate them, and remember the exact fields needing attention."""
    validation = LogicHandover(data).process()
    attention, validation_messages = _build_validation_attention(tasks, validation)
    task_groups = {
        "outstanding": [task for task in tasks if task.task_type == "outstanding"],
        "bau": [task for task in tasks if task.task_type == "bau"],
    }
    tasks_by_type = {
        "outstanding_tasks": task_groups["outstanding"],
        "bau_tasks": task_groups["bau"],
    }
    with transaction.atomic():
        for data_key, task_records in tasks_by_type.items():
            for task, record in zip(task_records, data.get(data_key, [])):
                task.title = record.get("task", "")
                task.description = record.get("description", "")

                if task.task_type == "outstanding":
                    task.deadline = _parse_handover_date(record.get("deadline"))
                else:
                    task.frequency = record.get("frequency", "")
                    task.start_date = _parse_handover_date(record.get("start_date"))
                    task.end_date = _parse_handover_date(record.get("end_date"))
                task.save()

                if task.task_type == "outstanding":
                    _replace_task_subtasks(task, record.get("subtasks", []))

        # Any saved edit makes the previously generated Word document outdated.
        if handover.completed_document:
            handover.completed_document.delete(save=False)
        handover.important_information = [
            item for item in (handover.important_information or [])
            if not str(item).startswith("⚠️ Needs Clarification:")
        ]
        if validation["status"] == "complete" and finalize:
            handover.status = "completed"
            messages.success(request, "The handover details are valid and the handover is now complete.")
        else:
            handover.status = "needs_clarification"
            handover.important_information.append(
                "⚠️ Needs Clarification: Some task details still need review."
            )
            if finalize:
                warning = "Your edits were saved, but some required details still need attention."
                if validation_messages:
                    warning += " " + " ".join(validation_messages)
                messages.warning(request, warning)
            else:
                messages.info(request, "AI suggestions applied. Review the highlighted fields, then choose Save and recheck.")
        handover.save(update_fields=["status", "important_information", "completed_document"])

    return validation_messages


def _saved_handover_data(handover, tasks):
    """Convert saved rows to the input format expected by Logic Manager."""
    data = {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": handover.important_information or [],
    }
    for task in tasks:
        owners = list(task.owners.all())
        record = {
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
            record["subtasks"] = []
            for subtask in task.subtasks.all():
                record["subtasks"].append({
                    "subtask_id": subtask.code,
                    "task": subtask.title,
                    "planned_date": subtask.planned_date.strftime("%d/%m/%Y") if subtask.planned_date else "",
                    "dependencies": [dependency.code for dependency in subtask.depends_on.all()],
                })
            data["outstanding_tasks"].append(record)
    return data


def attach_validation_attention(tasks, attention):
    """Expose validation messages beside the corresponding edit controls."""
    for task in tasks:
        task_attention = attention.get(str(task.pk), {})
        task.attention = task_attention.get("fields", {})
        for subtask in task.subtasks.all():
            subtask_attention = task_attention.get("subtasks", {}).get(str(subtask.pk), {})
            subtask.attention = subtask_attention.get("fields", {})


def _parse_handover_date(value):
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def _replace_task_subtasks(task, subtask_data):
    existing = {subtask.code: subtask for subtask in task.subtasks.all()}
    updated = {}
    for index, item in enumerate(subtask_data, start=1):
        code = item.get("subtask_id") or f"S{index:03d}"
        subtask = existing.get(code)
        if subtask is None:
            subtask = Subtask(task=task, code=code)
        subtask.title = item.get("task", "")
        subtask.planned_date = _parse_handover_date(item.get("planned_date"))
        subtask.save()
        updated[code] = subtask

    for subtask in existing.values():
        if subtask.code not in updated:
            subtask.delete()

    for item in subtask_data:
        subtask = updated[item.get("subtask_id")]
        dependencies = [
            updated[dependency]
            for dependency in item.get("dependencies", [])
            if dependency in updated
        ]
        subtask.depends_on.set(dependencies)


def render_handover_review(request, employee, upload, data, error_message=None):
    review_sections = build_review_sections(data)
    return render(request, "handovers/home.html", {
        "employee": employee,
        "review_mode": True,
        "review_sections": review_sections,
        "has_clarifications": any(
            task["clarification_questions"]
            for section in review_sections
            for task in section["tasks"]
        ),
        "review_error": error_message,
        "uploaded_filename": upload.original_name if upload else "",
        "important_information": data.get("important_information", []),
        "request_token": str(uuid4()),
    })


@login_required(login_url="handovers:login")
@require_POST
def cancel_handover_processing(request):
    employee = getattr(request.user, "employee", None)
    request_token = request.POST.get("request_token", "")
    if not employee or not valid_request_token(request_token):
        return JsonResponse({"cancelled": False}, status=400)

    cache.set(
        handover_cancel_key(employee, request_token),
        True,
        timeout=CANCEL_REQUEST_TIMEOUT,
    )
    return JsonResponse({
        "cancelled": True,
        "redirect_url": reverse("handovers:home"),
    })


@login_required(login_url="handovers:login")
def create_handover(request):
    employee = getattr(request.user, "employee", None)

    if request.method == "POST":
        action = request.POST.get("action", "upload")
        request_token = request.POST.get("request_token", "")

        if action in {"refine", "save", "cancel"}:
            upload_id = request.session.get(PENDING_UPLOAD_KEY)
            data = request.session.get(PENDING_DATA_KEY)
            upload = HandoverQuery().pending_upload(upload_id, employee)

            if not upload or not data:
                request.session.pop(PENDING_UPLOAD_KEY, None)
                request.session.pop(PENDING_DATA_KEY, None)
                return redirect("handovers:home")

            if action == "cancel":
                clear_pending_handover(request, upload)
                return redirect("handovers:home")

            if action == "refine":
                answers = collect_clarification_answers(data, request.POST)
                if not answers:
                    return render_handover_review(
                        request, employee, upload, data,
                        "Answer at least one clarification question before asking AI to refine the handover.",
                    )

                try:

                    input_handler = HandoverInputHandler()
                    input_handler.validate_clarification_answers(answers)

                    upload.file.open("rb")
                    try:
                        document_text = input_handler.process_upload(upload.file)
                    finally:
                        upload.file.close()

                    answer_text = "\n".join(
                        f"Task: {item['task']}\nQuestion: {item['question']}\nReviewer answer: {item['answer']}"
                        for item in answers
                    )
                    refined_prompt = (
                        f"{document_text}\n\n"
                        "REVIEWER ANSWERS TO CLARIFICATION QUESTIONS:\n"
                        f"{answer_text}\n\n"
                        "Revise the matching tasks using these answers."
                    )
                    if handover_cancelled(employee, request_token):
                        clear_pending_handover(request, upload)
                        return redirect("handovers:home")
                    result = HandoverCoordinator().review_handover(refined_prompt)
                except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
                    if handover_cancelled(employee, request_token):
                        clear_pending_handover(request, upload)
                        return redirect("handovers:home")
                    return render_handover_review(
                        request, employee, upload, data,
                        f"Could not refine the handover: {error}",
                    )

                if handover_cancelled(employee, request_token):
                    clear_pending_handover(request, upload)
                    return redirect("handovers:home")

                if not result["success"]:
                    return render_handover_review(
                        request, employee, upload, data,
                        f"Could not refine the handover: {result['error_message']}",
                    )

                request.session[PENDING_DATA_KEY] = result["data"]
                return redirect("handovers:home")

            owner_error = apply_owner_selections(data, request.POST)
            if owner_error:
                return render_handover_review(request, employee, upload, data, owner_error)

            logic_data = HandoverCoordinator.strip_clarification_questions(data)
            logic = LogicHandover(logic_data)
            processed = logic.process()

            has_questions = any(
                task.get("clarification_questions")
                for task in data.get("outstanding_tasks", []) + data.get("bau_tasks", [])
            )

            if processed["status"] == "complete" and not has_questions:
                try:
                    handover = HandoverRepository().save_handover(
                        employee, upload, processed, status="completed"
                    )
                except DataManagerError as error:
                    return render_handover_review(request, employee, upload, data, str(error))

                clear_pending_handover(request)
                messages.success(
                    request,
                    f"Handover H-{handover.pk:04d} was successfully marked as Complete and saved."
                )
                return redirect("handovers:handover_history")
            else:
                save_data = logic.get_task_records()
                missing_reasons = []
                if processed["status"] != "complete":
                    for err in processed.get("errors", []):
                        if isinstance(err, dict):
                            task_name = err.get("task", f"Task {err.get('index', '')}")
                            reasons = ", ".join(err.get("errors", []))
                            missing_reasons.append(f"{task_name} ({reasons})")
                        else:
                            missing_reasons.append(str(err))
                if has_questions:
                    missing_reasons.append("Unanswered clarification questions remain")

                if missing_reasons:
                    save_data.setdefault("important_information", []).append(
                        f"⚠️ Needs Clarification: Handover saved with pending items: {'; '.join(missing_reasons)}"
                    )

                try:
                    handover = HandoverRepository().save_handover(
                        employee, upload, save_data, status="needs_clarification"
                    )
                except DataManagerError as error:
                    return render_handover_review(request, employee, upload, data, str(error))

                clear_pending_handover(request)
                messages.warning(
                    request,
                    f"Handover H-{handover.pk:04d} was saved under 'Needs clarification' due to pending items ({'; '.join(missing_reasons)}). You can review it or download the draft document."
                )
                return redirect("handovers:handover_history")

        form = HandoverUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "handovers/home.html", {
                "form": form,
                "employee": employee,
                "request_token": str(uuid4()),
            })

        if form.is_valid():
            if not employee:
                return render(request, "handovers/home.html", {
                    "form": form,
                    "employee": employee,
                    "error_message": "Your employee profile could not be found.",
                    "request_token": str(uuid4()),
                })

            uploaded_file = form.cleaned_data["document"]
            try:
                try:
                    document_text = HandoverInputHandler().process_upload(uploaded_file)
                except ValueError as error:
                    return render(request, "handovers/home.html", {
                        "form": form,
                        "employee": employee,
                        "error_message": str(error),
                        "request_token": str(uuid4()),
                    })
                if handover_cancelled(employee, request_token):
                    return redirect("handovers:home")
                result = HandoverCoordinator().review_handover(document_text)
            except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
                result = {"success": False, "error_message": str(error)}

            if handover_cancelled(employee, request_token):
                return redirect("handovers:home")

            if not result.get("success"):
                try:
                    fallback_data = HandoverCoordinator.build_table_fallback_data(document_text)
                    result = {
                        "success": True,
                        "data": fallback_data,
                        "warning": f"Gemini AI is currently unavailable ({result.get('error_message', 'service offline')}). Tasks were extracted directly from the template tables. Please review and confirm all details manually.",
                    }
                except Exception as fallback_err:
                    return render(request, "handovers/home.html", {
                        "form": form,
                        "employee": employee,
                        "error_message": f"The document could not be reviewed: {result.get('error_message', fallback_err)}",
                        "request_token": str(uuid4()),
                    })

            uploaded_file.seek(0)
            upload = HandoverRepository().create_upload(uploaded_file, employee)
            if handover_cancelled(employee, request_token):
                HandoverRepository().delete_upload(upload)
                return redirect("handovers:home")
            request.session[PENDING_UPLOAD_KEY] = upload.pk
            request.session[PENDING_DATA_KEY] = result["data"]
            if handover_cancelled(employee, request_token):
                clear_pending_handover(request, upload)
                return redirect("handovers:home")
            if result.get("warning"):
                messages.warning(request, result["warning"])
            return redirect("handovers:home")
    else:
        upload_id = request.session.get(PENDING_UPLOAD_KEY)
        data = request.session.get(PENDING_DATA_KEY)
        upload = HandoverQuery().pending_upload(upload_id, employee)
        if upload and data:
            return render_handover_review(request, employee, upload, data)

    form = HandoverUploadForm()
    return render(request, "handovers/home.html", {
        "form": form,
        "employee": employee,
        "request_token": str(uuid4()),
    })


@login_required(login_url="handovers:login")
def my_tasks(request):
    employee = getattr(request.user, "employee", None)
    calendar_tasks = []
    unscheduled_tasks = []

    if employee:
        assigned_tasks = HandoverQuery().tasks_owned_by(employee)

        for task in assigned_tasks:
            handover_label = f"H-{task.handover_id:04d}"
            if task.task_type == "bau":
                calendar_tasks.append({
                    "id": f"task-{task.pk}",
                    "taskId": task.pk,
                    "title": task.title,
                    "handover": handover_label,
                    "type": "bau",
                    "startDate": task.start_date.isoformat() if task.start_date else None,
                    "endDate": task.end_date.isoformat() if task.end_date else None,
                    "frequency": task.frequency,
                    "completedDates": [
                        item.completion_date.isoformat()
                        for item in task.completions.all()
                    ],
                })
                continue

            subtasks = list(task.subtasks.all())
            has_planned_subtask = False
            for subtask in subtasks:
                if subtask.planned_date:
                    has_planned_subtask = True
                    calendar_tasks.append({
                        "id": f"subtask-{subtask.pk}",
                        "subtaskId": subtask.pk,
                        "taskId": task.pk,
                        "title": f"{subtask.code} {subtask.title}",
                        "parentTaskId": task.code,
                        "parentTask": task.title,
                        "handover": handover_label,
                        "type": "planned",
                        "date": subtask.planned_date.isoformat(),
                        "completed": subtask.status == "done",
                        "dependencies": [f"subtask-{dependency.pk}" for dependency in subtask.depends_on.all()],
                    })

            if task.deadline:
                calendar_tasks.append({
                    "id": f"deadline-{task.pk}",
                    "taskId": task.pk,
                    "title": task.title,
                    "handover": handover_label,
                    "type": "deadline",
                    "date": task.deadline.isoformat(),
                    "completed": task.is_completed,
                    "hasSubtasks": bool(subtasks),
                    "subtasksComplete": all(subtask.status == "done" for subtask in subtasks),
                    "subtaskIds": [f"subtask-{subtask.pk}" for subtask in subtasks],
                })
            elif not has_planned_subtask:
                # Keep saved tasks visible even when clarification is needed
                # before they can be placed on a specific calendar date.
                unscheduled_tasks.append({
                    "title": task.title,
                    "handover": handover_label,
                })

    return render(request, "handovers/my_tasks.html", {
        "employee": employee,
        "calendar_tasks": calendar_tasks,
        "unscheduled_tasks": unscheduled_tasks,
    })


@login_required(login_url="handovers:login")
@require_POST
def update_task_status(request, task_id):
    employee = getattr(request.user, "employee", None)
    if not employee:
        return JsonResponse({"error": "Employee profile unavailable."}, status=403)

    try:
        payload = json.loads(request.body)
        mark_done = payload.get("completed")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    if not isinstance(mark_done, bool):
        return JsonResponse({"error": "Invalid completion value."}, status=400)

    try:
        task = HandoverQuery().task_with_progress(task_id, employee)
    except DataManagerError as error:
        return JsonResponse({"error": str(error)}, status=503)
    if task is None:
        return JsonResponse({"error": "Task not found."}, status=404)

    if task.task_type == "bau":
        try:
            occurrence_date = date.fromisoformat(payload.get("date", ""))
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid occurrence date."}, status=400)

        if not is_bau_occurrence(task, occurrence_date):
            return JsonResponse({"error": "That date is not a scheduled occurrence of this BAU task."}, status=400)

        if mark_done:
            TaskCompletion.objects.get_or_create(
                task=task,
                completion_date=occurrence_date,
            )
        else:
            TaskCompletion.objects.filter(
                task=task,
                completion_date=occurrence_date,
            ).delete()
        return JsonResponse({"completed": mark_done})

    if task.task_type != "outstanding":
        return JsonResponse({"error": "Unsupported task type."}, status=400)

    if mark_done and task.subtasks.exists() and task.subtasks.exclude(status="done").exists():
        return JsonResponse({
            "error": "Complete all subtasks before marking this task complete."
        }, status=409)

    task.is_completed = mark_done
    task.save(update_fields=["is_completed"])
    return JsonResponse({"completed": mark_done})


def is_bau_occurrence(task, occurrence_date):
    if not task.start_date or occurrence_date < task.start_date:
        return False
    if task.end_date and occurrence_date > task.end_date:
        return False

    if task.frequency == "weekly":
        return (occurrence_date - task.start_date).days % 7 == 0
    if task.frequency == "monthly":
        return occurrence_date.day == task.start_date.day
    if task.frequency == "yearly":
        return (
            occurrence_date.month == task.start_date.month
            and occurrence_date.day == task.start_date.day
        )
    return occurrence_date == task.start_date


@login_required(login_url="handovers:login")
@require_POST
def update_subtask_status(request, subtask_id):
    employee = getattr(request.user, "employee", None)
    if not employee:
        return JsonResponse({"error": "Employee profile unavailable."}, status=403)

    try:
        payload = json.loads(request.body)
        mark_done = payload.get("completed")
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    if not isinstance(mark_done, bool):
        return JsonResponse({"error": "Invalid completion value."}, status=400)

    subtask = HandoverQuery().subtask_with_task(subtask_id)
    if subtask is None:
        return JsonResponse({"error": "Subtask not found."}, status=404)
    if not subtask.task.owners.filter(pk=employee.pk).exists():
        return JsonResponse({"error": "You are not assigned to this task."}, status=403)

    if mark_done:
        task_subtasks = list(subtask.task.subtasks.all())
        logic_subtasks = []
        for item in task_subtasks:
            logic_subtasks.append({
                "subtask_id": item.code,
                "task": item.title,
                "planned_date": item.planned_date.strftime("%d/%m/%Y") if item.planned_date else "",
                "dependencies": list(item.depends_on.values_list("code", flat=True)),
            })

        manager = OutstandingTask(
            name=subtask.task.title,
            description=subtask.task.description or "Task",
            owners=list(subtask.task.owners.values_list("name", flat=True)),
            owner_ids=list(subtask.task.owners.values_list("employee_id", flat=True)),
            deadline=(subtask.task.deadline or subtask.planned_date).strftime("%d/%m/%Y"),
            task_id=subtask.task_id,
            subtasks=logic_subtasks,
        )
        completed_codes = set(
            subtask.task.subtasks.filter(status="done").values_list("code", flat=True)
        )
        if not manager.can_complete_subtask(subtask.code, completed_codes):
            return JsonResponse({
                "error": "Complete the required earlier subtask(s) first."
            }, status=409)
    elif subtask.needed_by.filter(status="done").exists():
        return JsonResponse({
            "error": "A later dependent subtask is already complete. Undo that first."
        }, status=409)

    try:
        HandoverRepository().update_subtask_status(subtask, mark_done)
        if not mark_done and subtask.task.is_completed:
            subtask.task.is_completed = False
            subtask.task.save(update_fields=["is_completed"])
    except DataManagerError as error:
        return JsonResponse({"error": str(error)}, status=503)
    return JsonResponse({"completed": mark_done})


HISTORY_PAGE_SIZE = 10


@login_required(login_url="handovers:login")
def handover_history(request):
    """List the logged-in employee's handovers, with search, status filter and pages."""
    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()
    employee = getattr(request.user, "employee", None)

    handovers = HandoverQuery().search_handovers(employee, query, selected_status)

    total_count = len(handovers)
    page_obj = Paginator(handovers, HISTORY_PAGE_SIZE).get_page(
        request.GET.get("page", 1)
    )

    return render(request, "handovers/history.html", {
        "handovers": page_obj.object_list,
        "page_obj": page_obj,
        "query": query,
        "selected_status": selected_status,
        "status_choices": Handover.STATUS_CHOICES,   # [("active","Active"), ("completed","Completed")]
        "total_count": total_count,
        "employee": employee,
    })


@login_required(login_url="handovers:login")
def handover_detail(request, handover_id):
    """Show saved tasks and allow the creator to edit their handover."""
    employee = getattr(request.user, "employee", None)
    handover = get_object_or_404(
        Handover.objects.prefetch_related(
            "tasks__owners",
            Prefetch("tasks__subtasks", queryset=Subtask.objects.order_by("code").prefetch_related("depends_on")),
        ),
        pk=handover_id,
        created_by=employee,
    )

    detail_url = reverse("handovers:handover_detail", args=[handover.pk])
    edit_url = f"{detail_url}?edit=1"
    edit_mode = handover.status in ("completed", "needs_clarification") and (
        request.GET.get("edit") == "1"
        or (request.method == "POST" and request.POST.get("edit_mode") == "1")
    )
    edit_errors = []
    tasks = list(handover.tasks.all())
    if request.method == "POST":
        if handover.status not in ("completed", "needs_clarification"):
            messages.error(request, "This handover cannot be edited.")
            return redirect(detail_url)
        if not edit_mode:
            messages.error(request, "Open Edit handover before making changes.")
            return redirect(detail_url)

        action = request.POST.get("action", "save")
        suggestion_key = f"handover_ai_suggestions_{handover.pk}"
        tasks = list(handover.tasks.prefetch_related(
            "owners",
            Prefetch("subtasks", queryset=Subtask.objects.order_by("code").prefetch_related("depends_on")),
        ))

        if action == "discard_ai_suggestions":
            request.session.pop(suggestion_key, None)
            return redirect(edit_url)

        if action == "apply_ai_suggestions":
            suggested_data = request.session.get(suggestion_key)
            if not suggested_data:
                messages.error(request, "Those AI suggestions are no longer available. Please ask AI to refine again.")
                return redirect(edit_url)
            for data_key, task_type in (("outstanding_tasks", "outstanding"), ("bau_tasks", "bau")):
                existing_tasks = [task for task in tasks if task.task_type == task_type]
                suggested_tasks = suggested_data.get(data_key, [])
                if len(existing_tasks) != len(suggested_tasks):
                    request.session.pop(suggestion_key, None)
                    messages.error(request, "AI changed the number of tasks, so its suggestions were not applied.")
                    return redirect(edit_url)
                for existing_task, suggested_task in zip(existing_tasks, suggested_tasks):
                    owners = list(existing_task.owners.all())
                    suggested_task["task_id"] = existing_task.code
                    suggested_task["owners"] = [owner.name for owner in owners]
                    suggested_task["owner_ids"] = [owner.employee_id for owner in owners]
            persist_clarification_edits(
                request, handover, tasks, suggested_data, finalize=False
            )
            request.session.pop(suggestion_key, None)
            return redirect(edit_url)

        edit_data = {
            "outstanding_tasks": [],
            "bau_tasks": [],
            "important_information": handover.important_information or [],
        }

        def read_date(field_name, label):
            value = request.POST.get(field_name, "").strip()
            if not value:
                return "", None
            try:
                parsed_date = date.fromisoformat(value)
                return parsed_date.strftime("%d/%m/%Y"), parsed_date
            except ValueError:
                edit_errors.append(f"Enter a valid date for {label}.")
                return value, None

        for task in tasks:
            prefix = f"task_{task.pk}_"
            title = request.POST.get(f"{prefix}title", task.title).strip()
            description = request.POST.get(f"{prefix}description", task.description).strip()
            owners = list(task.owners.all())
            record = {
                "task_id": task.code,
                "task": title,
                "description": description,
                "owners": [owner.name for owner in owners],
                "owner_ids": [owner.employee_id for owner in owners],
            }
            if task.task_type == "bau":
                record["frequency"] = request.POST.get(f"{prefix}frequency", task.frequency).strip()
                record["start_date"], _ = read_date(
                    f"{prefix}start_date", f"{task.title} start date"
                )
                record["end_date"], _ = read_date(
                    f"{prefix}end_date", f"{task.title} end date"
                )
            else:
                record["deadline"], _ = read_date(
                    f"{prefix}deadline", f"{task.title} deadline"
                )
                record["subtasks"] = []
                for subtask in task.subtasks.all():
                    subtask_title = request.POST.get(
                        f"subtask_{subtask.pk}_title", subtask.title
                    ).strip()
                    planned_date_text, planned_date = read_date(
                        f"subtask_{subtask.pk}_planned_date",
                        f"{task.title} subtask {subtask.code} planned date",
                    )
                    record["subtasks"].append({
                        "subtask_id": subtask.code,
                        "task": subtask_title,
                        "planned_date": planned_date_text,
                        "dependencies": list(subtask.depends_on.values_list("code", flat=True)),
                    })

            edit_data["bau_tasks" if task.task_type == "bau" else "outstanding_tasks"].append(record)

        if edit_errors:
            messages.error(request, "Some dates were invalid. Please correct them and save again.")
        elif action == "ai_refine":
            request_token = request.POST.get("request_token", "")
            if handover_cancelled(employee, request_token):
                return redirect(edit_url)
            prompt = (
                "Review the following edited saved handover. Suggest clearer task details and sensible planned "
                "subtasks for outstanding tasks when useful. Keep exactly the same number and order of parent "
                "tasks in each task type, and keep every owner unchanged. Do not invent dates. Return the normal "
                "handover JSON structure. Draft data:\n"
                f"{json.dumps(edit_data, ensure_ascii=False)}"
            )
            result = HandoverCoordinator().review_handover(prompt)
            if handover_cancelled(employee, request_token):
                return redirect(edit_url)
            if not result.get("success"):
                messages.error(request, f"AI could not refine this handover: {result.get('error_message', 'Unknown error')}")
            else:
                suggestions = result["data"]
                same_task_counts = all(
                    len(suggestions.get(data_key, [])) == sum(task.task_type == task_type for task in tasks)
                    for data_key, task_type in (("outstanding_tasks", "outstanding"), ("bau_tasks", "bau"))
                )
                if not same_task_counts:
                    messages.error(request, "AI changed the number of tasks, so its suggestions were not saved.")
                else:
                    for data_key, task_type in (("outstanding_tasks", "outstanding"), ("bau_tasks", "bau")):
                        existing_tasks = [task for task in tasks if task.task_type == task_type]
                        for existing_task, suggestion in zip(existing_tasks, suggestions.get(data_key, [])):
                            owners = list(existing_task.owners.all())
                            suggestion["task_id"] = existing_task.code
                            suggestion["owners"] = [owner.name for owner in owners]
                            suggestion["owner_ids"] = [owner.employee_id for owner in owners]
                    normalize_ai_subtask_codes(suggestions, tasks)
                    request.session[suggestion_key] = suggestions
                    messages.info(request, "AI suggestions are ready. Review them below; they have not been applied yet.")
            return redirect(edit_url)
        else:
            request.session.pop(suggestion_key, None)
            persist_clarification_edits(request, handover, tasks, edit_data)
            if handover.status == "needs_clarification":
                return redirect(edit_url)
            return redirect(detail_url)

    attention = {}
    if handover.status == "needs_clarification":
        # Recheck saved details on every visit, including a fresh login or browser.
        saved_data = _saved_handover_data(handover, tasks)
        validation = LogicHandover(saved_data).process()
        attention, validation_messages = _build_validation_attention(tasks, validation)
    attach_validation_attention(tasks, attention)
    return render(request, "handovers/handover_detail.html", {
        "employee": employee,
        "handover": handover,
        "tasks": tasks,
        "edit_errors": edit_errors,
        "edit_mode": edit_mode,
        "detail_url": detail_url,
        "edit_url": edit_url,
        "ai_suggestions": request.session.get(f"handover_ai_suggestions_{handover.pk}"),
        "request_token": str(uuid4()),
    })


@login_required(login_url="handovers:login")
@require_POST
def delete_handover(request, handover_id):
    """Delete one handover owned by the signed-in employee."""
    employee = getattr(request.user, "employee", None)
    handover = get_object_or_404(Handover, pk=handover_id, created_by=employee)

    stored_files = [upload.file for upload in handover.uploads.all() if upload.file]
    if handover.completed_document:
        stored_files.append(handover.completed_document)

    handover.delete()
    for stored_file in stored_files:
        try:
            stored_file.delete(save=False)
        except OSError:
            logger.exception("Could not remove a stored file for deleted handover %s", handover_id)

    messages.success(request, f"Handover H-{handover_id:04d} was deleted.")
    return redirect("handovers:handover_history")


@login_required(login_url="handovers:login")
def download_completed_handover(request, handover_id):
    employee = get_object_or_404(Employee, user=request.user)

    # Only allow the logged-in employee to download their own handover
    handover = get_object_or_404(
        Handover,
        pk=handover_id,
        created_by=employee,
        status="completed",
    )

    # Generate and store the document on its first download request
    if not handover.completed_document:
        try:
            CompletedHandoverDocumentGenerator().save(handover)
        except (OSError, ValueError):
            logger.exception(
                "Could not generate handover document %s",
                handover.pk,
            )
            return HttpResponseServerError(
                "Could not generate the Word document. Please try again later."
            )

    return FileResponse(
        handover.completed_document.open("rb"),
        as_attachment=True,
        filename=f"handover-{handover.pk:04d}.docx",
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    )
