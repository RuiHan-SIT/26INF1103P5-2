import json
import logging
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import FileResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .data_manager.handover_query import HandoverQuery
from .forms import HandoverUploadForm
from .models import Employee, Handover, Subtask
from .services.cancellation_tracker import CancellationTracker
from .services.handover_clarification_service import HandoverClarificationService
from .services.handover_draft_service import HandoverDraftService
from .services.pending_draft_session import PendingDraftSession
from .services.task_execution_service import TaskExecutionService

logger = logging.getLogger(__name__)

HISTORY_PAGE_SIZE = 10


class HandoverController:
    """HTTP controller coordinating handover views with injected application services."""

    def __init__(
        self,
        draft_service=None,
        clarification_service=None,
        task_service=None,
        query=None,
        cancellation_tracker=None,
        session_cls=PendingDraftSession,
    ):
        self._draft_service = draft_service or HandoverDraftService()
        self._clarification_service = clarification_service or HandoverClarificationService()
        self._task_service = task_service or TaskExecutionService()
        self._query = query or HandoverQuery()
        self._cancellation = cancellation_tracker or CancellationTracker()
        self._session_cls = session_cls

    # ---- Draft & Upload endpoints ----------------------------------------

    def cancel_handover_processing(self, request):
        employee = getattr(request.user, "employee", None)
        request_token = request.POST.get("request_token", "")
        if not self._cancellation.cancel(employee, request_token):
            return JsonResponse({"cancelled": False}, status=400)
        return JsonResponse({
            "cancelled": True,
            "redirect_url": reverse("handovers:home"),
        })

    def create_handover(self, request):
        employee = getattr(request.user, "employee", None)
        draft_session = self._session_cls(request, query=self._query)

        if request.method != "POST":
            upload, data = draft_session.load(employee)
            if upload and data:
                return self._render_review_home(request, employee, upload, data)
            return self._render_upload_home(request, employee)

        action = request.POST.get("action", "upload")
        if action in {"refine", "save", "cancel"}:
            return self._dispatch_draft_action(request, employee, action, draft_session)

        return self._handle_upload_action(request, employee, draft_session)

    def _handle_upload_action(self, request, employee, draft_session):
        form = HandoverUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return self._render_upload_home(request, employee, form=form)

        request_token = request.POST.get("request_token", "")
        result = self._draft_service.upload_and_review(
            employee, form.cleaned_data["document"], request_token
        )
        if result["status"] == "cancelled":
            return redirect("handovers:home")
        if result["status"] == "error":
            return self._render_upload_home(
                request, employee, form=form, error_message=result["error_message"]
            )

        draft_session.save(result["upload"], result["data"])
        if result.get("warning"):
            messages.warning(request, result["warning"])
        return redirect("handovers:home")

    def _dispatch_draft_action(self, request, employee, action, draft_session):
        upload, data = draft_session.load(employee)
        if not upload or not data:
            return redirect("handovers:home")

        handlers = {
            "cancel": self._draft_cancel,
            "refine": self._draft_refine,
            "save": self._draft_save,
        }
        return handlers[action](request, employee, upload, data, draft_session)

    def _draft_cancel(self, request, employee, upload, data, draft_session):
        self._draft_service.cancel_draft(upload)
        draft_session.clear()
        return redirect("handovers:home")

    def _draft_refine(self, request, employee, upload, data, draft_session):
        request_token = request.POST.get("request_token", "")
        result = self._draft_service.refine_draft(
            employee, upload, data, request.POST, request_token
        )
        if result["status"] == "cancelled":
            return self._draft_cancel(request, employee, upload, data, draft_session)
        if result["status"] == "error":
            return self._render_review_home(
                request, employee, upload, data, result["error_message"]
            )
        draft_session.update_data(result["data"])
        return redirect("handovers:home")

    def _draft_save(self, request, employee, upload, data, draft_session):
        result = self._draft_service.save_draft(employee, upload, data, request.POST)
        if result["status"] in {"invalid", "error"}:
            return self._render_review_home(
                request, employee, upload, data, result["error_message"]
            )
        draft_session.clear()
        if result["status"] == "completed":
            messages.success(
                request,
                f"Handover H-{result['handover'].pk:04d} was successfully marked as Complete and saved.",
            )
        else:
            messages.warning(
                request,
                f"Handover H-{result['handover'].pk:04d} was saved under 'Needs clarification' "
                f"due to pending items ({'; '.join(result['missing_reasons'])}). "
                "You can review it or download the draft document.",
            )
        return redirect("handovers:handover_history")

    # ---- My Tasks & Execution endpoints ----------------------------------

    def my_tasks(self, request):
        employee = getattr(request.user, "employee", None)
        context = self._task_service.build_my_tasks_context(employee)
        context["employee"] = employee
        return render(request, "handovers/my_tasks.html", context)

    def update_task_status(self, request, task_id):
        payload, error_response = self._parse_completed_payload(request)
        if error_response:
            return error_response

        employee = getattr(request.user, "employee", None)
        result = self._task_service.update_task_status(
            employee=employee,
            task_id=task_id,
            mark_done=payload.get("completed"),
            occurrence_date_str=payload.get("date", ""),
        )
        return self._status_json_response(result)

    def update_subtask_status(self, request, subtask_id):
        payload, error_response = self._parse_completed_payload(request)
        if error_response:
            return error_response

        employee = getattr(request.user, "employee", None)
        result = self._task_service.update_subtask_status(
            employee=employee,
            subtask_id=subtask_id,
            mark_done=payload.get("completed"),
        )
        return self._status_json_response(result)

    # ---- History, Detail & Export endpoints ------------------------------

    def handover_history(self, request):
        query = request.GET.get("q", "").strip()
        selected_status = request.GET.get("status", "").strip()
        employee = getattr(request.user, "employee", None)

        handovers = self._query.search_handovers(employee, query, selected_status)
        page_obj = Paginator(handovers, HISTORY_PAGE_SIZE).get_page(
            request.GET.get("page", 1)
        )

        return render(request, "handovers/history.html", {
            "handovers": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "selected_status": selected_status,
            "status_choices": Handover.STATUS_CHOICES,
            "total_count": len(handovers),
            "employee": employee,
        })

    def handover_detail(self, request, handover_id):
        employee = getattr(request.user, "employee", None)
        subtask_prefetch = Prefetch(
            "tasks__subtasks",
            queryset=Subtask.objects.order_by("code").prefetch_related("depends_on"),
        )
        handover = get_object_or_404(
            Handover.objects.prefetch_related("tasks__owners", subtask_prefetch),
            pk=handover_id,
            created_by=employee,
        )

        detail_url = reverse("handovers:handover_detail", args=[handover.pk])
        edit_url = f"{detail_url}?edit=1"
        edit_mode = handover.status in ("completed", "needs_clarification") and (
            request.GET.get("edit") == "1"
            or (request.method == "POST" and request.POST.get("edit_mode") == "1")
        )
        tasks = list(handover.tasks.all())

        if request.method == "POST":
            if handover.status not in ("completed", "needs_clarification"):
                messages.error(request, "This handover cannot be edited.")
                return redirect(detail_url)
            if not edit_mode:
                messages.error(request, "Open Edit handover before making changes.")
                return redirect(detail_url)

            return self._dispatch_detail_post(
                request, employee, handover, tasks, detail_url, edit_url
            )

        self._clarification_service.attach_detail_attention(handover, tasks)
        return render(request, "handovers/handover_detail.html", {
            "employee": employee,
            "handover": handover,
            "tasks": tasks,
            "edit_errors": [],
            "edit_mode": edit_mode,
            "show_edit_shortcut": request.GET.get("rechecked") == "1",
            "detail_url": detail_url,
            "edit_url": edit_url,
            "ai_suggestions": request.session.get(f"handover_ai_suggestions_{handover.pk}"),
            "request_token": str(uuid4()),
        })

    def _dispatch_detail_post(
        self, request, employee, handover, tasks, detail_url, edit_url
    ):
        action = request.POST.get("action", "save")
        handlers = {
            "discard_ai_suggestions": self._detail_discard_ai,
            "apply_ai_suggestions": self._detail_apply_ai,
            "ai_refine": self._detail_ai_refine,
            "save": self._detail_save,
        }
        handler = handlers.get(action, self._detail_save)
        return handler(request, employee, handover, tasks, detail_url, edit_url)

    def _detail_discard_ai(self, request, employee, handover, tasks, detail_url, edit_url):
        request.session.pop(f"handover_ai_suggestions_{handover.pk}", None)
        return redirect(edit_url)

    def _detail_apply_ai(self, request, employee, handover, tasks, detail_url, edit_url):
        suggestion_key = f"handover_ai_suggestions_{handover.pk}"
        result = self._clarification_service.apply_ai_suggestions(
            handover, tasks, request.session.get(suggestion_key)
        )
        if result["clear_suggestions"]:
            request.session.pop(suggestion_key, None)
        (messages.success if result["success"] else messages.error)(request, result["message"])
        return redirect(edit_url)

    def _detail_ai_refine(self, request, employee, handover, tasks, detail_url, edit_url):
        suggestion_key = f"handover_ai_suggestions_{handover.pk}"
        request_token = request.POST.get("request_token", "")
        result = self._clarification_service.request_ai_refinement(
            employee, handover, tasks, request.POST, request_token
        )
        if result["status"] == "cancelled":
            return redirect(edit_url)
        if result["status"] == "ready":
            request.session[suggestion_key] = result["suggestions"]
            messages.info(request, result["message"])
        elif result.get("message"):
            messages.error(request, result["message"])
        return redirect(edit_url)

    def _detail_save(self, request, employee, handover, tasks, detail_url, edit_url):
        suggestion_key = f"handover_ai_suggestions_{handover.pk}"
        request.session.pop(suggestion_key, None)
        result = self._clarification_service.save_clarification_edits(
            handover, tasks, request.POST
        )
        if result["status"] == "invalid_dates":
            messages.error(
                request, "Some dates were invalid. Please correct them and save again."
            )
            self._clarification_service.attach_detail_attention(handover, tasks)
            return render(request, "handovers/handover_detail.html", {
                "employee": employee,
                "handover": handover,
                "tasks": tasks,
                "edit_errors": result["edit_errors"],
                "edit_mode": True,
                "detail_url": detail_url,
                "edit_url": edit_url,
                "ai_suggestions": request.session.get(suggestion_key),
                "request_token": str(uuid4()),
            })
        if result["status"] == "completed":
            messages.success(
                request, "The handover details are valid and the handover is now complete.",
            )
            return redirect(f"{detail_url}?rechecked=1")

        warning = "Your edits were saved, but some required details still need attention."
        if result["validation_messages"]:
            warning += " " + " ".join(result["validation_messages"])
        messages.warning(request, warning)
        return redirect(edit_url)

    def delete_handover(self, request, handover_id):
        employee = getattr(request.user, "employee", None)
        handover = get_object_or_404(Handover, pk=handover_id, created_by=employee)
        self._clarification_service.delete_handover(handover)
        messages.success(request, f"Handover H-{handover_id:04d} was deleted.")
        return redirect("handovers:handover_history")

    def download_completed_handover(self, request, handover_id):
        employee = get_object_or_404(Employee, user=request.user)
        handover = get_object_or_404(
            Handover,
            pk=handover_id,
            created_by=employee,
            status="completed",
        )

        try:
            self._clarification_service.ensure_completed_document(handover)
        except (OSError, ValueError):
            logger.exception("Could not generate handover document %s", handover.pk)
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

    # ---- Shared rendering & JSON helpers ---------------------------------

    @staticmethod
    def _render_upload_home(request, employee, form=None, error_message=None):
        return render(request, "handovers/home.html", {
            "form": form or HandoverUploadForm(),
            "employee": employee,
            "error_message": error_message,
            "request_token": str(uuid4()),
        })

    def _render_review_home(self, request, employee, upload, data, error_message=None):
        context = self._draft_service.build_review_context(
            employee, upload, data, error_message
        )
        context["request_token"] = str(uuid4())
        return render(request, "handovers/home.html", context)

    @staticmethod
    def _parse_completed_payload(request):
        try:
            payload = json.loads(request.body)
            return payload, None
        except (json.JSONDecodeError, AttributeError):
            return None, JsonResponse({"error": "Invalid request."}, status=400)

    @staticmethod
    def _status_json_response(result):
        if not result["success"]:
            return JsonResponse({"error": result["error_message"]}, status=result["status_code"])
        return JsonResponse({"completed": result["completed"]})


_controller = HandoverController()

cancel_handover_processing = login_required(login_url="handovers:login")(
    require_POST(_controller.cancel_handover_processing)
)
create_handover = login_required(login_url="handovers:login")(
    _controller.create_handover
)
my_tasks = login_required(login_url="handovers:login")(
    _controller.my_tasks
)
update_task_status = login_required(login_url="handovers:login")(
    require_POST(_controller.update_task_status)
)
update_subtask_status = login_required(login_url="handovers:login")(
    require_POST(_controller.update_subtask_status)
)
handover_history = login_required(login_url="handovers:login")(
    _controller.handover_history
)
handover_detail = login_required(login_url="handovers:login")(
    _controller.handover_detail
)
delete_handover = login_required(login_url="handovers:login")(
    require_POST(_controller.delete_handover)
)
download_completed_handover = login_required(login_url="handovers:login")(
    _controller.download_completed_handover
)
