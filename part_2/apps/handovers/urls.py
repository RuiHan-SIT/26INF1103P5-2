from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from . import views

app_name = "handovers"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html"
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            success_url=reverse_lazy("handovers:password_change_done"),
        ),
        name="password_change",
    ),
    path(
        "password-change/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="registration/password_change_done.html"
        ),
        name="password_change_done",
    ),
    path("", RedirectView.as_view(
        pattern_name="handovers:login",
        permanent=False
    ),
    name="index",
    ),
    path("create-handover/", views.create_handover,name="home"),
    path("create-handover/", views.create_handover, name="create_handover"),
    path("my-tasks/", views.my_tasks, name="my_tasks"),
    path("my-tasks/subtasks/<int:subtask_id>/status/", views.update_subtask_status, name="update_subtask_status"),
    path("history/", views.handover_history, name="handover_history"),
    path(
        "history/<int:handover_id>/download/",
        views.download_completed_handover,
        name="download_completed_handover",
    ),
]