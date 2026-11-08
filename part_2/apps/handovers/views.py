from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required(login_url='handovers:login')
def home(request):
    return render(request, 'handovers/home.html', {
        'title': 'Handover Management System'
    })
