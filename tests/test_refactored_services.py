from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from apps.handovers.data_manager.handover_repository import HandoverRepository
from apps.handovers.input_handler.handover_input_handler import HandoverInputHandler
from apps.handovers.logic_manager.bau_task import BAUTask
from apps.handovers.logic_manager.outstanding_task import OutstandingTask
from apps.handovers.services.cancellation_tracker import CancellationTracker
from apps.handovers.services.handover_clarification_service import HandoverClarificationService
from apps.handovers.services.handover_draft_service import HandoverDraftService
from apps.handovers.services.handover_mapper import HandoverDraftMapper
from apps.handovers.services.task_execution_service import TaskExecutionService


def test_cancellation_tracker_round_trip():
    store = {}

    class FakeCache:
        def set(self, key, value, timeout=None):
            store[key] = value

        def get(self, key):
            return store.get(key)

    tracker = CancellationTracker(cache_backend=FakeCache())
    employee = SimpleNamespace(pk=7)
    token = "12345678-1234-5678-1234-567812345678"

    assert tracker.is_valid_token(token) is True
    assert tracker.is_valid_token("not-a-uuid") is False
    assert tracker.cancel(employee, "not-a-uuid") is False
    assert tracker.is_cancelled(employee, token) is False

    assert tracker.cancel(employee, token) is True
    assert tracker.is_cancelled(employee, token) is True


def test_mapper_collects_clarification_answers_and_builds_review_sections():
    mapper = HandoverDraftMapper()
    data = {
        "outstanding_tasks": [
            {
                "task": "Migrate DB",
                "description": "Move sqlite to postgres",
                "owners": ["Alice"],
                "clarification_questions": ["What is the deadline?", "Who approves?"],
            }
        ],
        "bau_tasks": [],
    }
    employees = [
        {"employee_id": "E001", "name": "Alice Tan", "department": "IT"},
        {"employee_id": "E002", "name": "Bob Lim", "department": "HR"},
    ]

    sections = mapper.build_review_sections(data, employees)
    assert len(sections) == 1
    assert sections[0]["title"] == "One-off tasks"
    assert len(sections[0]["tasks"][0]["clarification_questions"]) == 2

    answers = mapper.collect_clarification_answers(
        data,
        {
            "clarification_outstanding_0_0": " 30/12/2026 ",
            "clarification_outstanding_0_1": "   ",
        },
    )
    assert answers == [
        {
            "task": "Migrate DB",
            "question": "What is the deadline?",
            "answer": "30/12/2026",
        }
    ]


def test_draft_service_upload_uses_table_fallback_when_ai_offline():
    input_handler = MagicMock()
    input_handler.process_upload.return_value = "Task 1:\nTask: Audit\nOwner: Alice"

    coordinator = MagicMock()
    coordinator.review_handover.return_value = {
        "success": False,
        "error_message": "API down",
    }

    fake_upload = SimpleNamespace(pk=12, original_name="handover.docx")
    repository = MagicMock()
    repository.create_upload.return_value = fake_upload

    cancellation = MagicMock()
    cancellation.is_cancelled.return_value = False

    service = HandoverDraftService(
        input_handler=input_handler,
        coordinator=coordinator,
        repository=repository,
        query=MagicMock(),
        mapper=HandoverDraftMapper(),
        cancellation_tracker=cancellation,
    )

    uploaded_file = MagicMock()
    result = service.upload_and_review(SimpleNamespace(pk=1), uploaded_file, "token")

    assert result["status"] == "ready"
    assert result["upload"] is fake_upload
    assert "API down" in result["warning"]
    uploaded_file.seek.assert_called_once_with(0)
    repository.create_upload.assert_called_once()


def test_draft_service_save_marks_needs_clarification_when_questions_remain():
    employee = SimpleNamespace(employee_id="E001", name="Alice Tan", department="IT")
    query = MagicMock()
    query.all_employees.return_value = [employee]

    saved_handover = SimpleNamespace(pk=99)
    repository = MagicMock()
    repository.save_handover.return_value = saved_handover

    service = HandoverDraftService(
        input_handler=MagicMock(),
        coordinator=MagicMock(),
        repository=repository,
        query=query,
        mapper=HandoverDraftMapper(),
        cancellation_tracker=MagicMock(),
    )

    data = {
        "outstanding_tasks": [
            {
                "task_id": "T1",
                "task": "Close tickets",
                "description": "Resolve all open P1 tickets",
                "owners": ["Alice"],
                "deadline": "31/12/2099",
                "subtasks": [],
                "clarification_questions": ["Confirm ticket count?"],
            }
        ],
        "bau_tasks": [],
        "important_information": [],
    }
    post_data = {
        "owner_outstanding_0_0": "E001",
        "owner_confirmed_outstanding_0_0": "yes",
    }

    result = service.save_draft(employee, SimpleNamespace(pk=5), data, post_data)

    assert result["status"] == "needs_clarification"
    assert result["handover"] is saved_handover
    assert "Unanswered clarification questions remain" in result["missing_reasons"]
    assert repository.save_handover.call_args.kwargs["status"] == "needs_clarification"


def test_clarification_service_rejects_mismatched_ai_suggestion_counts():
    service = HandoverClarificationService(
        coordinator=MagicMock(),
        mapper=HandoverDraftMapper(),
        cancellation_tracker=MagicMock(),
        document_generator=MagicMock(),
    )
    tasks = [SimpleNamespace(task_type="outstanding")]
    suggested = {"outstanding_tasks": [], "bau_tasks": []}

    result = service.apply_ai_suggestions(SimpleNamespace(pk=1), tasks, suggested)

    assert result["success"] is False
    assert result["clear_suggestions"] is True
    assert "changed the number of tasks" in result["message"]


def test_task_execution_service_bau_occurrence_and_guards():
    weekly_task = SimpleNamespace(
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 30),
        frequency="weekly",
    )
    assert TaskExecutionService.is_bau_occurrence(weekly_task, date(2026, 11, 9)) is True
    assert TaskExecutionService.is_bau_occurrence(weekly_task, date(2026, 11, 10)) is False
    assert TaskExecutionService.is_bau_occurrence(weekly_task, date(2026, 12, 7)) is False

    monthly_task = SimpleNamespace(
        start_date=date(2026, 1, 15),
        end_date=None,
        frequency="monthly",
    )
    assert TaskExecutionService.is_bau_occurrence(monthly_task, date(2026, 5, 15)) is True
    assert TaskExecutionService.is_bau_occurrence(monthly_task, date(2026, 5, 16)) is False

    service = TaskExecutionService(query=MagicMock(), repository=MagicMock())
    res = service.update_task_status(None, 1, True)
    assert res["success"] is False
    assert res["status_code"] == 403


def test_handover_input_handler_validate_clarification_answers_and_di():
    # Test optional dependency injection
    mock_input_val = MagicMock()
    mock_file_val = MagicMock()
    mock_doc_reader = MagicMock()
    mock_input_val.validate_user_input.return_value = False

    handler_di = HandoverInputHandler(
        input_validator=mock_input_val,
        file_validator=mock_file_val,
        document_reader=mock_doc_reader,
    )
    assert handler_di.input_validator is mock_input_val
    assert handler_di.file_validator is mock_file_val
    assert handler_di.document_reader is mock_doc_reader

    assert handler_di.validate_clarification_answers([{"answer": "valid answer"}]) is True
    mock_input_val.validate_user_input.assert_called_once_with("valid answer")

    # Test default handler catches sensitive info in second answer
    handler = HandoverInputHandler()
    assert handler.validate_clarification_answers([
        {"answer": "First clean answer"},
        {"answer": "Second clean answer"},
    ]) is True

    # 1st is clean, 2nd contains sensitive keyword 'password'
    answers_with_sensitive_second = [
        {"answer": "Everything is deployed smoothly."},
        {"answer": "The server password is supersecret!"},
    ]
    with pytest.raises(ValueError, match="Sensitive information detected in clarification answer."):
        handler.validate_clarification_answers(answers_with_sensitive_second)

    # Non-string answer raises ValueError
    with pytest.raises(ValueError, match="Clarification answers must contain text."):
        handler.validate_clarification_answers([{"answer": 12345}])


def test_task_execution_service_is_bau_occurrence_month_end_and_leap_year_clamping():
    # Monthly: Jan 31 -> Feb 28 in non-leap year (and Mar 31, Apr 30)
    monthly_task = SimpleNamespace(
        start_date=date(2026, 1, 31),
        end_date=None,
        frequency="monthly",
    )
    assert TaskExecutionService.is_bau_occurrence(monthly_task, date(2026, 2, 28)) is True
    assert TaskExecutionService.is_bau_occurrence(monthly_task, date(2026, 2, 27)) is False
    assert TaskExecutionService.is_bau_occurrence(monthly_task, date(2026, 3, 31)) is True
    assert TaskExecutionService.is_bau_occurrence(monthly_task, date(2026, 4, 30)) is True
    assert TaskExecutionService.is_bau_occurrence(monthly_task, date(2026, 4, 29)) is False

    # Yearly: Feb 29 (leap year 2024) -> Feb 28 in non-leap years (2025, 2026), Feb 29 in leap year 2028
    yearly_task = SimpleNamespace(
        start_date=date(2024, 2, 29),
        end_date=None,
        frequency="yearly",
    )
    assert TaskExecutionService.is_bau_occurrence(yearly_task, date(2025, 2, 28)) is True
    assert TaskExecutionService.is_bau_occurrence(yearly_task, date(2025, 2, 27)) is False
    assert TaskExecutionService.is_bau_occurrence(yearly_task, date(2026, 2, 28)) is True
    assert TaskExecutionService.is_bau_occurrence(yearly_task, date(2028, 2, 29)) is True
    assert TaskExecutionService.is_bau_occurrence(yearly_task, date(2028, 2, 28)) is False


def test_task_from_dict_and_subclass_polymorphism():
    # OutstandingTask.from_dict
    data_out = {
        "task_id": "OUT-101",
        "task": "Deploy release",
        "description": "Deploy release v2",
        "owners": ["Alice Tan"],
        "owner_ids": ["EMP-001"],
        "deadline": "31/12/2026",
        "subtasks": [
            {
                "subtask_id": "S001",
                "task": "Run tests",
                "planned_date": "30/12/2026",
                "dependencies": [],
            }
        ],
    }
    task_out = OutstandingTask.from_dict(data_out)
    assert isinstance(task_out, OutstandingTask)
    assert task_out.get_name() == "Deploy release"
    assert task_out.validate() == []
    exported_out = task_out.to_dict()
    assert exported_out["task_id"] == "OUT-101"
    assert exported_out["deadline"] == "31/12/2026"
    assert len(exported_out["subtasks"]) == 1

    # BAUTask.from_dict
    data_bau = {
        "task_id": "BAU-202",
        "task": "Weekly standup",
        "description": "Sync team priorities",
        "owners": ["Bob Lim"],
        "owner_ids": ["EMP-002"],
        "frequency": "weekly",
        "start_date": date.today().strftime("%d/%m/%Y"),
        "end_date": (date.today() + timedelta(days=30)).strftime("%d/%m/%Y"),
    }
    task_bau = BAUTask.from_dict(data_bau)
    assert isinstance(task_bau, BAUTask)
    assert task_bau.get_name() == "Weekly standup"
    assert task_bau.validate() == []
    exported_bau = task_bau.to_dict()
    assert exported_bau["task_id"] == "BAU-202"
    assert exported_bau["frequency"] == "weekly"
    assert exported_bau["start_date"] == date.today().strftime("%d/%m/%Y")
    assert exported_bau["end_date"] == (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")

    # Concrete _validate_base via subclasses
    invalid_out = OutstandingTask.from_dict({"task": "", "description": "", "owners": []})
    errors = invalid_out.validate()
    assert "task" in errors
    assert "description" in errors
    assert "missing_owner(s)" in errors
    assert "missing_deadline" in errors


def test_handover_mapper_allocate_subtask_code_and_repo_parse_date():
    used = {"S001"}
    code, next_code = HandoverDraftMapper.allocate_subtask_code("VERY_LONG_SUBTASK_CODE", used, 1)
    assert code == "S002"
    assert next_code == 3

    assert HandoverRepository._parse_date("15/11/2026") == date(2026, 11, 15)
    assert HandoverRepository._parse_date("invalid") is None


def test_handover_controller_dependency_injection():
    from apps.handovers.views import HandoverController

    task_service = MagicMock()
    task_service.update_task_status.return_value = {"success": True, "status_code": 200, "completed": True}
    cancellation = MagicMock()
    cancellation.cancel.return_value = False

    controller = HandoverController(
        draft_service=MagicMock(),
        clarification_service=MagicMock(),
        task_service=task_service,
        query=MagicMock(),
        cancellation_tracker=cancellation,
    )

    fake_user = SimpleNamespace(employee=SimpleNamespace(pk=3))
    cancel_req = SimpleNamespace(user=fake_user, POST={"request_token": "bad"})
    resp = controller.cancel_handover_processing(cancel_req)
    assert resp.status_code == 400

    status_req = SimpleNamespace(user=fake_user, body=b'{"completed": true, "date": "2026-11-15"}')
    resp_ok = controller.update_task_status(status_req, task_id=42)
    assert resp_ok.status_code == 200
    task_service.update_task_status.assert_called_once()
