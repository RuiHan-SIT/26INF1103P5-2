import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import FileResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404, render

from .forms import HandoverUploadForm
from .models import Employee, Handover
from .output.word_document_generator import CompletedHandoverDocumentGenerator

logger = logging.getLogger(__name__)


@login_required(login_url='handovers:login')
def home(request):
    uploaded_filename = None

    if request.method == "POST":
        form = HandoverUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_filename = form.cleaned_data["document"].name
    else:
        form = HandoverUploadForm()

    return render(request, "handovers/home.html", {
        "title": "Handover Management System",
        "form": form,
        "uploaded_filename": uploaded_filename
    })


@login_required(login_url='handovers:login')
def handover_history(request):
    """List the logged-in employee's handovers, with search and status filter."""
    employee = get_object_or_404(Employee, user=request.user)

    # Only this employee's handovers (newest first, set in the model's Meta),
    # each with a count of its tasks
    all_handovers = Handover.objects.filter(created_by=employee).annotate(task_count=Count("tasks"))
    handovers = all_handovers

    # What the user typed in the search box and picked in the status dropdown
    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()

    # Search by ID: accepts "7", "H7" or "H-0007"
    if query:
        number = query.upper().replace("H", "").replace("-", "").strip()
        handovers = handovers.filter(pk=int(number)) if number.isdigit() else handovers.none()

    # Filter by status ("active" / "completed")
    if selected_status:
        handovers = handovers.filter(status=selected_status)

    return render(request, "handovers/history.html", {
        "handovers": handovers,
        "query": query,
        "selected_status": selected_status,
        "status_choices": Handover.STATUS_CHOICES,   # [("active","Active"), ("completed","Completed")]
        "total_count": all_handovers.count(),
    })


@login_required(login_url="handovers:login")
def download_completed_handover(request, handover_id):
    employee = get_object_or_404(Employee, user=request.user)

    # Only allow the logged-in employee to download their own completed handover
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