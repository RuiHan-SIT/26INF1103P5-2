from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import HandoverUploadForm

import logging

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponseServerError
from django.shortcuts import get_object_or_404
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


STATUS_CHOICES = ["Completed", "Needs clarification"]

# TEMPORARY sample data so the page can be built and tested on its own.
# Later this list comes from the DatabaseManager: the handovers created by the
# logged-in employee (id, title, created date, task count, status).
SAMPLE_HANDOVERS = [
    {"id": "H-0010", "title": "System Patch Handover", "created_on": "14 Nov 2026, 10:24 AM", "tasks": 6, "status": "Completed"},
    {"id": "H-0009", "title": "Project A Handover", "created_on": "12 Nov 2026, 4:17 PM", "tasks": 8, "status": "Completed"},
    {"id": "H-0008", "title": "Monthly Operations Handover", "created_on": "7 Nov 2026, 11:03 AM", "tasks": 5, "status": "Completed"},
    {"id": "H-0007", "title": "Access Review Handover", "created_on": "3 Nov 2026, 2:09 PM", "tasks": 4, "status": "Completed"},
    {"id": "H-0006", "title": "Network Upgrade Handover", "created_on": "28 Oct 2026, 9:45 AM", "tasks": 3, "status": "Needs clarification"},
]


def handover_history(request):
    """Show the handovers created by the logged-in employee, with search and filter."""
    # What the user typed in the search box and picked in the status dropdown
    query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()

    handovers = SAMPLE_HANDOVERS

    # Search: match the handover ID or the title (ignoring upper/lower case)
    if query:
        needle = query.lower()
        handovers = [
            h for h in handovers
            if needle in h["id"].lower() or needle in h["title"].lower()
        ]

    # Filter: keep only the chosen status
    if selected_status:
        handovers = [
            h for h in handovers
            if h["status"] == selected_status
        ]
    

    return render(request, "handovers/history.html", {
        "handovers": handovers,
        "query": query,
        "selected_status": selected_status,
        "status_choices": STATUS_CHOICES,
        "total_count": len(SAMPLE_HANDOVERS),
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