from django.urls import path
from . import views

app_name = 'handovers'

urlpatterns = [
    path('', views.home, name='home'),
    path('history/', views.handover_history, name='handover_history'),
]
