from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.core.paginator import Paginator

from .forms import HandoverUploadForm
from .models import Employee, Subtask, Task, Upload
from .logic_manager.employee_identity_matcher import EmployeeIdentityMatcher
from .logic_manager.handover import Handover as LogicHandover
from .logic_manager.outstanding_task import OutstandingTask
from .data_manager.handover_repository import HandoverRepository


PENDING_UPLOAD_KEY = "pending_handover_upload_id"
PENDING_DATA_KEY = "pending_handover_data"


def build_review_sections(data):
    employees = list(Employee.objects.values("employee_id", "name", "department"))
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
    employee_records = list(Employee.objects.all())
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
            upload = Upload.objects.filter(
                pk=upload_id,
                uploaded_by=employee,
                handover__isnull=True,
            ).first()

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
                    from .input_handler.handover_input_handler import HandoverInputHandler
                    from .services.handover_coordinator import HandoverCoordinator

                    upload.file.open("rb")
                    try:
                        document_text = HandoverInputHandler().process_upload(upload.file)
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
            processed = LogicHandover(logic_data).process()
            if processed["status"] != "complete":
                return render_handover_review(
                    request,
                    employee,
                    upload,
                    data,
                    "Some tasks are missing required details or have invalid dates. Answer their clarification questions, ask AI to refine them, then try saving again.",
                )

            try:
                HandoverRepository().save_handover(employee, upload, processed)
            except (IntegrityError, ValueError) as error:
                return render_handover_review(
                    request, employee, upload, data,
                    f"The handover could not be saved: {error}",
                )

            request.session.pop(PENDING_UPLOAD_KEY, None)
            request.session.pop(PENDING_DATA_KEY, None)
            return redirect("handovers:my_tasks")

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
                from .input_handler.handover_input_handler import HandoverInputHandler
                from .services.handover_coordinator import HandoverCoordinator

                document_text = HandoverInputHandler().process_upload(uploaded_file)
                result = HandoverCoordinator().review_handover(document_text)
            except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
                return render(request, "handovers/home.html", {
                    "form": form,
                    "employee": employee,
                    "error_message": f"The document could not be reviewed: {error}",
                })

            if not result["success"]:
                return render(request, "handovers/home.html", {
                    "form": form,
                    "employee": employee,
                    "error_message": f"The document could not be reviewed: {result['error_message']}",
                })

            uploaded_file.seek(0)
            upload = Upload.objects.create(
                file=uploaded_file,
                original_name=uploaded_file.name,
                size_bytes=uploaded_file.size,
                uploaded_by=employee,
            )
            request.session[PENDING_UPLOAD_KEY] = upload.pk
            request.session[PENDING_DATA_KEY] = result["data"]
            return redirect("handovers:home")
    else:
        upload_id = request.session.get(PENDING_UPLOAD_KEY)
        data = request.session.get(PENDING_DATA_KEY)
        upload = Upload.objects.filter(
            pk=upload_id,
            uploaded_by=employee,
            handover__isnull=True,
        ).first()
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

    if employee:
        assigned_tasks = (
            Task.objects.filter(owners=employee)
            .select_related("handover")
            .prefetch_related("subtasks__depends_on")
            .distinct()
        )

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

            for subtask in task.subtasks.all():
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

    return render(request, "handovers/my_tasks.html", {
        "employee": employee,
        "calendar_tasks": calendar_tasks,
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

    subtask = get_object_or_404(
        Subtask.objects.select_related("task").prefetch_related("task__subtasks__depends_on"),
        pk=subtask_id,
    )
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


STATUS_CHOICES = ["Completed", "Needs clarification"]
HISTORY_PAGE_SIZE = 10

# Temporary examples for History until handovers are connected to the database.
SAMPLE_HANDOVERS = [
    {"id": "H-0010", "title": "System Patch Handover", "created_on": "14 Nov 2026, 10:24 AM", "tasks": 6, "status": "Completed"},
    {"id": "H-0009", "title": "Project A Handover", "created_on": "12 Nov 2026, 4:17 PM", "tasks": 8, "status": "Completed"},
    {"id": "H-0008", "title": "Monthly Operations Handover", "created_on": "7 Nov 2026, 11:03 AM", "tasks": 5, "status": "Completed"},
    {"id": "H-0007", "title": "Access Review Handover", "created_on": "3 Nov 2026, 2:09 PM", "tasks": 4, "status": "Completed"},
    {"id": "H-0006", "title": "Network Upgrade Handover", "created_on": "28 Oct 2026, 9:45 AM", "tasks": 3, "status": "Needs clarification"},
]


@login_required(login_url="handovers:login")
def handover_history(request):
    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()
    employee = getattr(request.user, "employee", None)

    handovers = SAMPLE_HANDOVERS

    if query:
        needle = query.lower()
        handovers = [
            handover for handover in handovers
            if needle in handover["id"].lower()
            or needle in handover["title"].lower()
        ]

    if selected_status:
        handovers = [
            handover for handover in handovers
            if handover["status"] == selected_status
        ]

    total_count = len(handovers)
    page_obj = Paginator(handovers, HISTORY_PAGE_SIZE).get_page(
        request.GET.get("page", 1)
    )

    return render(request, "handovers/history.html", {
        "handovers": page_obj.object_list,
        "page_obj": page_obj,
        "query": query,
        "selected_status": selected_status,
        "status_choices": STATUS_CHOICES,
        "total_count": total_count,
        "employee": employee,
    })
