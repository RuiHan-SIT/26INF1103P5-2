import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
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
    mock_handover.created_at = datetime(2026, 11, 12, tzinfo=timezone.utc)
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


@patch("apps.handovers.data_manager.handover_repository.transaction.atomic")
@patch("apps.handovers.data_manager.handover_repository.Handover.objects.create")
@patch("apps.handovers.data_manager.handover_repository.Task.objects.create")
@patch("apps.handovers.data_manager.handover_repository.Subtask.objects.create")
def test_handover_repository_save_needs_clarification(
    mock_subtask_create, mock_task_create, mock_handover_create, mock_atomic
):
    from apps.handovers.data_manager.handover_repository import HandoverRepository

    mock_employee = MagicMock()
    mock_employee.pk = 1
    mock_upload = MagicMock()
    mock_handover = MagicMock()
    mock_handover_create.return_value = mock_handover
    mock_task = MagicMock()
    mock_task_create.return_value = mock_task

    processed_data = {
        "important_information": ["⚠️ Needs Clarification: Task 1 has no deadline"],
        "outstanding_tasks": [
            {
                "task": "Task without deadline",
                "description": "Some description",
                "owner_ids": [1],
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
    result = repo.save_handover(mock_employee, mock_upload, processed_data, status="needs_clarification")

    assert result is mock_handover
    mock_handover_create.assert_called_once_with(
        created_by=mock_employee,
        important_information=processed_data["important_information"],
        status="needs_clarification",
    )
    mock_task_create.assert_called_once_with(
        handover=mock_handover,
        code="OUT-001",
        task_type="outstanding",
        title="Task without deadline",
        description="Some description",
        deadline=None,
    )
    mock_subtask_create.assert_called_once_with(
        task=mock_task,
        code="S001",
        title="Subtask without date",
        planned_date=None,
    )
    assert mock_upload.handover == mock_handover
    mock_upload.save.assert_called_once_with(update_fields=["handover"])
