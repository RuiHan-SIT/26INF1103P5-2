from django.shortcuts import render


def home(request):
    return render(request, 'handovers/home.html', {
        'title': 'Handover Management System'
    })

def create_handover(request):
    return render(request, 'handovers/create_handover.html')