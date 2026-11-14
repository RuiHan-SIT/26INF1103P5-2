import json
from datetime import timedelta
from django.utils import timezone
from unittest.mock import MagicMock
from apps.handovers.services.handover_service import HandoverService
from apps.handovers.services.handover_coordinator import HandoverCoordinator
from apps.handovers.services.llm_service import LLMService


class MockLLM(LLMService):
    def __init__(self, response_text: str):
        self.response_text = response_text

    def generate(self, prompt: str, system_instruction: str = None) -> str:
        return self.response_text


def test_pass_1_review_document_success():
    ai_response = """
    {
      "outstanding_tasks": [
        {
          "task": "Migrate database",
          "description": "Run Django migrations on staging",
          "owners": ["Rui Han"],
          "deadline": "25/11/2026",
          "subtasks": [],
          "clarification_questions": ["What is the staging DB host?"]
        }
      ],
      "bau_tasks": [
        {
          "task": "Weekly health check",
          "description": "Check service metrics",
          "owners": ["Ti Seng"],
          "frequency": "weekly",
          "start_date": "01/11/2026",
          "end_date": "30/11/2026",
          "clarification_questions": []
        }
      ],
      "important_information": ["DB password updated"]
    }
    """
    coordinator = HandoverCoordinator(llm_service=MockLLM(ai_response))
    service = HandoverService(coordinator=coordinator)

    response_data = json.loads(ai_response)
    start = timezone.localdate() + timedelta(days=1)
    response_data["bau_tasks"][0]["start_date"] = start.strftime("%d/%m/%Y")
    response_data["bau_tasks"][0]["end_date"] = (start + timedelta(days=30)).strftime("%d/%m/%Y")
    response_data["outstanding_tasks"][0]["deadline"] = (start + timedelta(days=7)).strftime("%d/%m/%Y")
    coordinator = HandoverCoordinator(llm_service=MockLLM(json.dumps(response_data)))
    service = HandoverService(coordinator=coordinator)
    result = service.review_document(
        "Task 1:\nTask Name: Weekly health check\nTask Type: Recurring\nFrequency: weekly"
    )

    assert result["ai_success"] is True
    assert result["error_message"] is None

    # Draft preserves clarification_questions for the UI
    assert len(result["draft"]["outstanding_tasks"]) == 1
    assert result["draft"]["outstanding_tasks"][0]["clarification_questions"] == [
        "What is the staging DB host?"
    ]

    # Logic manager validated the tasks without error
    assert result["validation"]["status"] == "complete"
    assert len(result["validation"]["outstanding_tasks"]) == 1
    assert len(result["validation"]["bau_tasks"]) == 1


def test_pass_1_handles_ai_failure_using_coordinator_fallback():
    mock_llm = MagicMock(spec=LLMService)
    mock_llm.generate.side_effect = RuntimeError("Rate limit exceeded (429)")

    coordinator = HandoverCoordinator(llm_service=mock_llm)
    service = HandoverService(coordinator=coordinator)

    result = service.review_document("Some raw notes")

    assert result["ai_success"] is False
    assert "Rate limit exceeded" in result["error_message"]

    # Clean fallback from HandoverCoordinator
    assert result["draft"] == HandoverCoordinator.FALLBACK_DATA
    assert result["draft"]["important_information"] == []

    # Logic manager receives fallback without crashing
    assert result["validation"]["status"] == "incomplete"
    assert result["validation"]["errors"] == [
        {"type": "handover", "errors": ["no_tasks"]}
    ]


def test_pass_2_update_draft_task_resolves_missing_fields_and_clears_questions():
    # Pass 1: Task is missing deadline and has a clarification question
    ai_response = """
    {
      "outstanding_tasks": [
        {
          "task": "Update server credentials",
          "description": "Rotate DB passwords",
          "owners": ["Rui Han"],
          "deadline": "",
          "subtasks": [],
          "clarification_questions": ["Which server cluster needs updating?"]
        }
      ],
      "bau_tasks": [],
      "important_information": []
    }
    """
    coordinator = HandoverCoordinator(llm_service=MockLLM(ai_response))
    service = HandoverService(coordinator=coordinator)

    pass1 = service.review_document("Rotate DB passwords")
    assert pass1["validation"]["status"] == "incomplete"
    assert pass1["validation"]["errors"][0]["errors"] == ["missing_deadline"]

    # Pass 2: User answers clarification question in description and supplies deadline
    pass2 = service.update_draft_task(
        draft_data=pass1["draft"],
        task_type="outstanding",
        task_id="OUT-1",
        task_changes={
            "description": "Rotate DB passwords on prod-db-01",
            "deadline": "25/11/2026"
        }
    )

    assert pass2["update_result"]["status"] == "updated"
    assert pass2["validation"]["status"] == "complete"
    assert pass2["draft"]["outstanding_tasks"][0]["description"] == "Rotate DB passwords on prod-db-01"
    assert pass2["draft"]["outstanding_tasks"][0]["deadline"] == "25/11/2026"
    assert pass2["draft"]["outstanding_tasks"][0]["clarification_questions"] == []
