import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count
from django.http import FileResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .data_manager.handover_repository import HandoverRepository
from .forms import HandoverUploadForm
from .logic_manager.employee_identity_matcher import EmployeeIdentityMatcher
from .logic_manager.handover import Handover as LogicHandover
from .logic_manager.outstanding_task import OutstandingTask
from .data_manager.handover_query import HandoverQuery
from .models import Employee, Handover
from .output.word_document_generator import CompletedHandoverDocumentGenerator
from .input_handler.handover_input_handler import HandoverInputHandler
from .services.handover_coordinator import HandoverCoordinator

logger = logging.getLogger(__name__)


PENDING_UPLOAD_KEY = "pending_handover_upload_id"
PENDING_DATA_KEY = "pending_handover_data"


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


def render_handover_review(request, employee, upload, data, error_message=None, preview_mode=False):
    review_sections = build_review_sections(data)
    return render(request, "handovers/home.html", {
        "employee": employee,
        "review_mode": True,
        "preview_mode": preview_mode,
        "review_sections": review_sections,
        "has_clarifications": any(
            task["clarification_questions"]
            for section in review_sections
            for task in section["tasks"]
        ),
        "review_error": error_message,
        "uploaded_filename": upload.original_name if upload else (
            "Sample handover.docx" if preview_mode else ""
        ),
        "important_information": data.get("important_information", []),
    })


@login_required(login_url="handovers:login")
def create_handover(request):
    employee = getattr(request.user, "employee", None)

    if request.method == "POST":
        action = request.POST.get("action", "upload")

        if action == "preview_names":
            owner_names = [
                name.strip()
                for name in request.POST.get("demo_names", "").splitlines()
                if name.strip()
            ]
            if not owner_names:
                return render(request, "handovers/home.html", {
                    "form": HandoverUploadForm(),
                    "employee": employee,
                    "demo_names": request.POST.get("demo_names", ""),
                    "demo_error": "Enter at least one name, with one name on each line.",
                })

            preview_data = {
                "outstanding_tasks": [{
                    "task": "Sample task for owner matching",
                    "description": "Preview only. No AI call or handover save.",
                    "owners": owner_names,
                    "clarification_questions": [],
                }],
                "bau_tasks": [],
                "important_information": [],
            }
            return render_handover_review(
                request, employee, None, preview_data, preview_mode=True
            )

        if action == "demo_cancel":
            return redirect("handovers:home")

        if action == "demo_confirm":
            owner_names = request.POST.getlist("demo_owner_name")
            preview_data = {
                "outstanding_tasks": [{
                    "task": "Sample task for owner matching",
                    "description": "Preview only. No AI call or handover save.",
                    "owners": owner_names,
                    "clarification_questions": [],
                }],
                "bau_tasks": [],
                "important_information": [],
            }
            owner_error = apply_owner_selections(preview_data, request.POST)
            if owner_error:
                return render_handover_review(
                    request, employee, None, preview_data, owner_error,
                    preview_mode=True,
                )

            demo_result = [
                {"extracted_name": source_name, "employee_name": selected_name}
                for source_name, selected_name in zip(
                    owner_names, preview_data["outstanding_tasks"][0]["owners"]
                )
            ]
            return render(request, "handovers/home.html", {
                "form": HandoverUploadForm(),
                "employee": employee,
                "demo_result": demo_result,
            })

        if action in {"refine", "save", "cancel"}:
            upload_id = request.session.get(PENDING_UPLOAD_KEY)
            data = request.session.get(PENDING_DATA_KEY)
            upload = HandoverQuery().pending_upload(upload_id, employee)

            if not upload or not data:
                request.session.pop(PENDING_UPLOAD_KEY, None)
                request.session.pop(PENDING_DATA_KEY, None)
                return redirect("handovers:home")

            if action == "cancel":
                HandoverRepository().delete_upload(upload)
                request.session.pop(PENDING_UPLOAD_KEY, None)
                request.session.pop(PENDING_DATA_KEY, None)
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
                    result = HandoverCoordinator().review_handover(refined_prompt)
                except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
                    return render_handover_review(
                        request, employee, upload, data,
                        f"Could not refine the handover: {error}",
                    )

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
                except (IntegrityError, ValueError) as error:
                    return render_handover_review(
                        request, employee, upload, data,
                        f"The handover could not be saved: {error}",
                    )

                request.session.pop(PENDING_UPLOAD_KEY, None)
                request.session.pop(PENDING_DATA_KEY, None)
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
                except (IntegrityError, ValueError) as error:
                    return render_handover_review(
                        request, employee, upload, data,
                        f"The handover could not be saved: {error}",
                    )

                request.session.pop(PENDING_UPLOAD_KEY, None)
                request.session.pop(PENDING_DATA_KEY, None)
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
            })

        if form.is_valid():
            if not employee:
                return render(request, "handovers/home.html", {
                    "form": form,
                    "employee": employee,
                    "error_message": "Your employee profile could not be found.",
                })

            uploaded_file = form.cleaned_data["document"]
            try:
                document_text = HandoverInputHandler().process_upload(uploaded_file)
                result = HandoverCoordinator().review_handover(document_text)
            except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
                result = {"success": False, "error_message": str(error)}

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
                    })

            uploaded_file.seek(0)
            upload = HandoverRepository().create_upload(uploaded_file, employee)
            request.session[PENDING_UPLOAD_KEY] = upload.pk
            request.session[PENDING_DATA_KEY] = result["data"]
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
                    "title": task.title,
                    "handover": handover_label,
                    "type": "bau",
                    "startDate": task.start_date.isoformat() if task.start_date else None,
                    "endDate": task.end_date.isoformat() if task.end_date else None,
                    "frequency": task.frequency,
                })
                continue

            has_planned_subtask = False
            for subtask in task.subtasks.all():
                if subtask.planned_date:
                    has_planned_subtask = True
                    calendar_tasks.append({
                        "id": f"subtask-{subtask.pk}",
                        "subtaskId": subtask.pk,
                        "title": f"{subtask.code} {subtask.title}",
                        "handover": handover_label,
                        "type": "planned",
                        "date": subtask.planned_date.isoformat(),
                        "completed": subtask.status == "done",
                        "dependencies": [f"subtask-{dependency.pk}" for dependency in subtask.depends_on.all()],
                    })

            if task.deadline:
                calendar_tasks.append({
                    "id": f"deadline-{task.pk}",
                    "title": task.title,
                    "handover": handover_label,
                    "type": "deadline",
                    "date": task.deadline.isoformat(),
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
                "planned_date": item.planned_date.strftime("%d/%m/%Y"),
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

    HandoverRepository().update_subtask_status(subtask, mark_done)
    return JsonResponse({"completed": mark_done})


HISTORY_PAGE_SIZE = 10


@login_required(login_url="handovers:login")
def handover_history(request):
    """List the logged-in employee's handovers, with search, status filter and pages."""
    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()
    employee = getattr(request.user, "employee", None)

    # Only this employee's handovers (newest first, set in the model's Meta),
    # each with a count of its tasks
    if employee:
        handovers = Handover.objects.filter(created_by=employee).annotate(task_count=Count("tasks"))
    else:
        handovers = Handover.objects.none()

    # Search by ID: accepts "7", "H7" or "H-0007"
    if query:
        number = query.upper().replace("H", "").replace("-", "").strip()
        handovers = handovers.filter(pk=int(number)) if number.isdigit() else handovers.none()

    # Filter by status ("active" / "completed")
    if selected_status:
        handovers = handovers.filter(status=selected_status)

    total_count = handovers.count()
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
    """Show the saved tasks and details for one handover in the user's history."""
    employee = getattr(request.user, "employee", None)
    handover = get_object_or_404(
        Handover.objects.prefetch_related("tasks__owners", "tasks__subtasks__depends_on"),
        pk=handover_id,
        created_by=employee,
    )
    return render(request, "handovers/handover_detail.html", {
        "employee": employee,
        "handover": handover,
        "tasks": handover.tasks.all(),
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
        status__in=["completed", "needs_clarification"],
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
