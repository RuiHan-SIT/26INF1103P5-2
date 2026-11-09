from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .forms import HandoverUploadForm


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
def create_handover(request):
    uploaded_filename = None
    employee = getattr(request.user, "employee", None)

    if request.method == "POST":
        print("POST REQUIRED RECEIVED")
        print("FILES", request.FILES)
        form = HandoverUploadForm(request.POST, request.FILES)

        if form.is_valid():
            print("Form is valid!")
            uploaded_file = form.cleaned_data["document"]
            uploaded_filename = uploaded_file.name

        else:
            print("Form is invalid!")
            print("ERRORS:", form.errors)
    else:
        form = HandoverUploadForm()

    return render(request, "handovers/create_handover.html", {
        "form": form,
        "uploaded_filename": uploaded_filename,
        "employee": employee,
    })
