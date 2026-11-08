from django.shortcuts import render
from .forms import HandoverUploadForm

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
