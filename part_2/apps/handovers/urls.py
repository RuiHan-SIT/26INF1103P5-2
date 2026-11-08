from django.urls import path
from . import views

app_name = 'handovers'

urlpatterns = [
    path('', views.home, name='home'),
    path('create-handover/', views.create_handover, name='create_handover'),
]
