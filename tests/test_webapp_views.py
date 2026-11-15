import io
import json
import tempfile
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from docx import Document

from apps.handovers.models import Employee, Handover, Subtask, Task


def _make_docx_bytes(text: str = "Handover notes for Q4.") -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class WebAppEndToEndTests(TestCase):
    def test_webapp_end_to_end_flows(self):
        start_date = timezone.localdate() + timedelta(days=1)
        next_occurrence = start_date + timedelta(days=7)
        media_root = tempfile.mkdtemp()
        with override_settings(
            MEDIA_ROOT=media_root,
            ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
        ):
            client = Client()

            # 1. Root redirects to login; protected route redirects when anonymous
            resp_index = client.get(reverse("handovers:index"))
            assert resp_index.status_code == 302
            assert reverse("handovers:login") in resp_index["Location"]

            resp_anon = client.get(reverse("handovers:home"))
            assert resp_anon.status_code == 302

            # 2. Setup authenticated employee & colleague
            user = User.objects.create_user(username="test_emp_9999991", password="secret")
            emp = Employee.objects.create(
                employee_id="9999991",
                name="Test Alice",
                department="Engineering",
                user=user,
            )
            client.force_login(user)

            # 3. GET /create-handover/ shows upload form
            resp_home = client.get(reverse("handovers:home"))
            assert resp_home.status_code == 200
            assert "Upload" in resp_home.content.decode()

            # 4. POST /create-handover/ (upload) -> AI extraction -> session draft
            fake_ai_data = {
                "outstanding_tasks": [
                    {
                        "task_id": "OUT-1",
                        "task": "Deploy Release",
                        "description": "Deploy v2 to production",
                        "owners": ["Test Alice"],
                        "owner_ids": [],
                        "deadline": "",
                        "subtasks": [
                            {
                                "subtask_id": "S001",
                                "task": "Run migrations",
                                "planned_date": "20/12/2099",
                                "dependencies": [],
                            }
                        ],
                        "clarification_questions": ["What is the exact release deadline?"],
                    }
                ],
                "bau_tasks": [
                    {
                        "task_id": "BAU-1",
                        "task": "Weekly Backup Check",
                        "description": "Verify backups every Monday",
                        "owners": ["Test Alice"],
                        "owner_ids": [],
                        "frequency": "weekly",
                        "start_date": start_date.strftime("%d/%m/%Y"),
                        "end_date": None,
                        "clarification_questions": [],
                    }
                ],
                "important_information": ["Staging environment is green."],
            }
            docx_file = SimpleUploadedFile(
                "handover.docx",
                _make_docx_bytes("Deploy Release and Weekly Backup Check"),
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            with patch(
                "apps.handovers.services.handover_coordinator.HandoverCoordinator.review_handover",
                return_value={"success": True, "data": fake_ai_data, "error_message": None},
            ):
                resp_upload = client.post(
                    reverse("handovers:create_handover"),
                    {"action": "upload", "document": docx_file, "request_token": "tok"},
                )
            assert resp_upload.status_code == 302

            # 5. GET /create-handover/ now renders review mode with extracted tasks & questions
            resp_review = client.get(reverse("handovers:home"))
            assert resp_review.status_code == 200
            review_html = resp_review.content.decode()
            assert "Deploy Release" in review_html
            assert "What is the exact release deadline?" in review_html

            # Required AI review cannot be bypassed by posting Save directly.
            bypass = client.post(reverse("handovers:create_handover"), {"action": "save"})
            assert bypass.status_code == 200
            assert Handover.objects.filter(created_by=emp).count() == 0

            # If refinement fails, the draft stays usable through field-validation fallback.
            with patch("apps.handovers.services.handover_coordinator.HandoverCoordinator.review_handover",
                       side_effect=RuntimeError("AI unavailable")):
                refined = client.post(reverse("handovers:create_handover"), {
                    "action": "refine", "clarification_outstanding_0_0": "The deadline is not confirmed yet",
                    "owner_outstanding_0_0": "9999991", "owner_confirmed_outstanding_0_0": "yes",
                    "owner_bau_0_0": "9999991", "owner_confirmed_bau_0_0": "yes",
                })
            assert refined.status_code == 302
            fallback_page = client.get(reverse("handovers:home"))
            assert "One-off tasks need a deadline." in fallback_page.content.decode()
            assert "Verify task owner" not in fallback_page.content.decode()

            # 6. POST /create-handover/ (save with missing deadline & unanswered question -> needs_clarification)
            resp_save = client.post(
                reverse("handovers:create_handover"),
                {
                    "action": "save",
                    "owner_outstanding_0_0": "9999991",
                    "owner_confirmed_outstanding_0_0": "yes",
                    "owner_bau_0_0": "9999991",
                    "owner_confirmed_bau_0_0": "yes",
                },
            )
            assert resp_save.status_code == 302
            assert resp_save["Location"] == reverse("handovers:handover_history")

            handover = Handover.objects.filter(created_by=emp).latest("pk")
            assert handover.status == "needs_clarification"

            # 7. GET /history/ lists the saved handover
            resp_hist = client.get(
                reverse("handovers:handover_history"),
                {"q": f"H-{handover.pk:04d}", "status": "needs_clarification"},
            )
            assert resp_hist.status_code == 200
            assert f"H-{handover.pk:04d}" in resp_hist.content.decode()

            # 8. GET & POST /history/<id>/ (edit_mode=1, action=save) fixes deadline -> promotes to completed
            out_task = Task.objects.get(handover=handover, task_type="outstanding")
            bau_task = Task.objects.get(handover=handover, task_type="bau")
            subtask = Subtask.objects.get(task=out_task)

            resp_detail_get = client.get(
                reverse("handovers:handover_detail", args=[handover.pk]),
                {"edit": "1"},
            )
            assert resp_detail_get.status_code == 200
            assert "Deploy Release" in resp_detail_get.content.decode()

            resp_detail_save = client.post(
                reverse("handovers:handover_detail", args=[handover.pk]),
                {
                    "edit_mode": "1",
                    "action": "save",
                    f"task_{out_task.pk}_title": "Deploy Release",
                    f"task_{out_task.pk}_description": "Deploy v2 to production",
                    f"task_{out_task.pk}_deadline": "2099-12-31",
                    f"subtask_{subtask.pk}_title": "Run migrations",
                    f"subtask_{subtask.pk}_planned_date": "2099-12-20",
                    f"task_{bau_task.pk}_title": "Weekly Backup Check",
                    f"task_{bau_task.pk}_description": "Verify backups every Monday",
                    f"task_{bau_task.pk}_frequency": "weekly",
                    f"task_{bau_task.pk}_start_date": start_date.isoformat(),
                    f"task_{bau_task.pk}_end_date": "",
                },
            )
            assert resp_detail_save.status_code == 302
            handover.refresh_from_db()
            assert handover.status == "completed"

            # 9. GET /history/<id>/download/ streams the generated .docx
            resp_dl = client.get(
                reverse("handovers:download_completed_handover", args=[handover.pk])
            )
            assert resp_dl.status_code == 200
            assert "wordprocessingml.document" in resp_dl["Content-Type"]
            # Consume stream without closing the underlying DB connection prematurely
            _ = b"".join(resp_dl.streaming_content)

            # 10. GET /my-tasks/ and POST subtask + task status endpoints
            resp_tasks = client.get(reverse("handovers:my_tasks"))
            assert resp_tasks.status_code == 200
            tasks_html = resp_tasks.content.decode()
            assert "Deploy Release" in tasks_html
            assert "Weekly Backup Check" in tasks_html

            # Cannot complete parent task before subtask is done
            resp_task_blocked = client.post(
                reverse("handovers:update_task_status", args=[out_task.pk]),
                data=json.dumps({"completed": True}),
                content_type="application/json",
            )
            assert resp_task_blocked.status_code == 409

            # Complete subtask first, then parent task
            resp_sub_done = client.post(
                reverse("handovers:update_subtask_status", args=[subtask.pk]),
                data=json.dumps({"completed": True}),
                content_type="application/json",
            )
            assert resp_sub_done.status_code == 200
            assert resp_sub_done.json() == {"completed": True}

            resp_task_done = client.post(
                reverse("handovers:update_task_status", args=[out_task.pk]),
                data=json.dumps({"completed": True}),
                content_type="application/json",
            )
            assert resp_task_done.status_code == 200
            assert resp_task_done.json() == {"completed": True}

            # Complete a BAU occurrence
            resp_bau_done = client.post(
                reverse("handovers:update_task_status", args=[bau_task.pk]),
                data=json.dumps({"completed": True, "date": next_occurrence.isoformat()}),
                content_type="application/json",
            )
            assert resp_bau_done.status_code == 200
            assert resp_bau_done.json() == {"completed": True}

            # Creator reviews a fifth work item before saving; recipient calendar has no warning.
            assert 'id="workload-warning"' not in client.get(reverse("handovers:my_tasks")).content.decode()
            for number in range(3):
                extra = Task.objects.create(handover=handover, code=f"EX-{number}",
                                            title=f"Existing weekly task {number}", description="Review checks",
                                            task_type="bau", frequency="weekly", start_date=start_date)
                extra.owners.add(emp)
            candidate = {
                "outstanding_tasks": [{"task": "New review", "description": "Prepare review",
                                       "owners": ["Test Alice"], "deadline": "31/12/2099",
                                       "subtasks": [{"subtask_id": "S001", "task": "Review evidence",
                                                     "planned_date": next_occurrence.strftime("%d/%m/%Y"), "dependencies": []}],
                                       "clarification_questions": []}],
                "bau_tasks": [], "important_information": []
            }
            with patch("apps.handovers.services.handover_coordinator.HandoverCoordinator.review_handover",
                       return_value={"success": True, "data": candidate, "error_message": None}):
                client.post(reverse("handovers:create_handover"), {
                    "action": "upload", "document": SimpleUploadedFile("another.docx", _make_docx_bytes("Prepare review"),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                })
            count_before = Handover.objects.filter(created_by=emp).count()
            save_payload = {"action": "save", "owner_outstanding_0_0": "9999991", "owner_confirmed_outstanding_0_0": "yes"}
            warning_page = client.post(reverse("handovers:create_handover"), save_payload)
            assert warning_page.status_code == 200
            warning_html = warning_page.content.decode()
            assert "Test Alice has 5 scheduled work items" in warning_html
            assert Handover.objects.filter(created_by=emp).count() == count_before
            import re
            token = re.search(r'name="acknowledge_workload" value="([^"]+)"', warning_html).group(1)
            save_payload["acknowledge_workload"] = token
            saved_anyway = client.post(reverse("handovers:create_handover"), save_payload)
            assert saved_anyway.status_code == 302
            assert Handover.objects.filter(created_by=emp).count() == count_before + 1

            # 11. POST /history/<id>/delete/ deletes the handover
            resp_del = client.post(
                reverse("handovers:delete_handover", args=[handover.pk])
            )
            assert resp_del.status_code == 302
            assert not Handover.objects.filter(pk=handover.pk).exists()
