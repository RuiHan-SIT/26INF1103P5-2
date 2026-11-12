import pytest
from datetime import date
from unittest.mock import MagicMock
from apps.handovers.logic_manager.handover import Handover
from apps.handovers.logic_manager.outstanding_task import OutstandingTask
from apps.handovers.services.handover_coordinator import HandoverCoordinator
from apps.handovers.output.word_document_generator import CompletedHandoverDocumentGenerator


def test_outstanding_task_get_deadline_safe():
    task_with_deadline = OutstandingTask("Task 1", "Desc", ["Alice"], "25/12/2026")
    assert task_with_deadline.get_deadline() is not None
    assert task_with_deadline.get_deadline().year == 2026

    task_no_deadline = OutstandingTask("Task 2", "Desc", ["Alice"], "")
    assert task_no_deadline.get_deadline() is None

    task_none_deadline = OutstandingTask("Task 3", "Desc", ["Alice"], None)
    assert task_none_deadline.get_deadline() is None


def test_handover_get_task_records_on_incomplete():
    # A handover missing a deadline on an outstanding task
    raw_data = {
        "important_information": ["Review passwords"],
        "outstanding_tasks": [
            {
                "task": "Task without deadline",
                "description": "Pending discussion",
                "owners": ["Alice"],
                "deadline": None,
                "subtasks": [],
            }
        ],
        "bau_tasks": [],
    }
    handover = Handover(raw_data)
    result = handover.process()
    assert result["status"] == "incomplete"

    records = handover.get_task_records()
    assert len(records["outstanding_tasks"]) == 1
    assert records["outstanding_tasks"][0]["task"] == "Task without deadline"
    assert records["outstanding_tasks"][0]["deadline"] is None
    assert records["important_information"] == ["Review passwords"]


def test_coordinator_build_table_fallback_data():
    sample_text = """
Task 1:
Task Name: Database Migration
Description: Migrate legacy tables
Task Owner(s): Bob Tan
Task Type: Outstanding
Deadline: 15/12/2026
Frequency:
Start Date:
End Date:

Task 2:
Task Name: Daily Monitoring
Description: Check server health
Task Owner(s): Charlie
Task Type: BAU
Deadline:
Frequency: Daily
Start Date: 01/12/2026
End Date:
"""
    fallback_data = HandoverCoordinator.build_table_fallback_data(sample_text)
    assert len(fallback_data["outstanding_tasks"]) == 1
    assert fallback_data["outstanding_tasks"][0]["task"] == "Database Migration"
    assert fallback_data["outstanding_tasks"][0]["owners"] == ["Bob Tan"]
    assert fallback_data["outstanding_tasks"][0]["deadline"] == "15/12/2026"

    assert len(fallback_data["bau_tasks"]) == 1
    assert fallback_data["bau_tasks"][0]["task"] == "Daily Monitoring"
    assert fallback_data["bau_tasks"][0]["frequency"] == "Daily"
    assert fallback_data["bau_tasks"][0]["start_date"] == "01/12/2026"

    assert any("Gemini AI was unavailable" in note for note in fallback_data["important_information"])


def test_word_export_supports_needs_clarification():
    mock_handover = MagicMock()
    mock_handover.status = "needs_clarification"
    mock_handover.pk = 42
    mock_handover.created_by.name = "Alice Tan"
    mock_handover.created_by.employee_id = "EMP-001"
    mock_handover.created_at = date(2026, 11, 12)
    mock_handover.important_information = ["⚠️ Needs Clarification: Missing deadline on Task 1"]

    task_mock = MagicMock()
    task_mock.task_type = "outstanding"
    task_mock.title = "Pending Task"
    task_mock.description = "Waiting for client input"
    task_mock.owners.all.return_value = []
    task_mock.deadline = None

    subtask_mock = MagicMock()
    subtask_mock.title = "Subtask 1"
    subtask_mock.planned_date = None
    subtask_mock.depends_on.all.return_value = []

    task_mock.subtasks.all.return_value = [subtask_mock]
    mock_handover.tasks.prefetch_related.return_value = [task_mock]

    generator = CompletedHandoverDocumentGenerator()
    # Ensure save() generates document content without raising ValueError
    content_file = generator.save(mock_handover)
    assert mock_handover.completed_document.save.called


def test_handover_repository_save_needs_clarification():
    import os, sys
    import django
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
        django.setup()

    from apps.handovers.data_manager.handover_repository import HandoverRepository
    from apps.handovers.models import Employee, Handover, Task, Subtask, Upload
    from django.contrib.auth.models import User
    from django.core.files.uploadedfile import SimpleUploadedFile

    user, _ = User.objects.get_or_create(username="testuser_clarify")
    employee, _ = Employee.objects.get_or_create(
        user=user, defaults={"name": "Test User", "employee_id": "TEST-001"}
    )
    dummy_file = SimpleUploadedFile("test.docx", b"dummy content")
    upload = Upload.objects.create(
        file=dummy_file,
        original_name="test.docx",
        size_bytes=13,
        uploaded_by=employee
    )

    processed_data = {
        "important_information": ["⚠️ Needs Clarification: Task 1 has no deadline"],
        "outstanding_tasks": [
            {
                "task": "Task without deadline",
                "description": "Some description",
                "owner_ids": [employee.pk],
                "deadline": None,
                "subtasks": [
                    {
                        "subtask_id": "S001",
                        "task": "Subtask without date",
                        "planned_date": None,
                        "dependencies": [],
                    }
                ],
            }
        ],
        "bau_tasks": [],
    }

    repo = HandoverRepository()
    handover = repo.save_handover(employee, upload, processed_data, status="needs_clarification")

    assert handover.status == "needs_clarification"
    assert handover.tasks.count() == 1
    task = handover.tasks.first()
    assert task.deadline is None
    assert task.subtasks.count() == 1
    subtask = task.subtasks.first()
    assert subtask.planned_date is None

    # Cleanup test artifacts
    upload.delete()
    handover.delete()
    user.delete()
