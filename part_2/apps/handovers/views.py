from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.contrib.auth.decorators import login_required

from .forms import HandoverUploadForm
from .models import Subtask, Task
from .logic_manager.outstanding_task import OutstandingTask


@login_required(login_url="handovers:login")
def create_handover(request):
    uploaded_filename = None
    employee = getattr(request.user, "employee", None)

    if request.method == "POST":
        form = HandoverUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = form.cleaned_data["document"]
            uploaded_filename = uploaded_file.name
    else:
        form = HandoverUploadForm()

    return render(request, "handovers/home.html", {
        "form": form,
        "uploaded_filename": uploaded_filename,
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

    subtask.status = "done" if mark_done else "todo"
    subtask.save(update_fields=["status"])
    return JsonResponse({"completed": mark_done})


STATUS_CHOICES = ["Completed", "Needs clarification"]

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

    return render(request, "handovers/history.html", {
        "handovers": handovers,
        "query": query,
        "selected_status": selected_status,
        "status_choices": STATUS_CHOICES,
        "total_count": len(SAMPLE_HANDOVERS),
        "employee": employee,
    })
