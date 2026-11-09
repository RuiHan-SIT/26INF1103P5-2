import json
from unittest.mock import MagicMock
from apps.handovers.services.handover_coordinator import HandoverCoordinator
from apps.handovers.services.llm_service import LLMService
from apps.handovers.logic_manager.handover import Handover


class MockLLM(LLMService):
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.last_prompt = None
        self.last_system_instruction = None

    def generate(self, prompt: str, system_instruction: str = None) -> str:
        self.last_prompt = prompt
        self.last_system_instruction = system_instruction
        return self.response_text


def test_coordinator_dependency_injection():
    mock_service = MockLLM("{}")
    coordinator = HandoverCoordinator(llm_service=mock_service)
    assert coordinator.llm_service is mock_service


def test_coordinator_review_handover_success_with_markdown_fences():
    mock_response = """
    ```json
    {
      "outstanding_tasks": [
        {
          "task": "Update server credentials",
          "description": "Rotate database passwords",
          "owners": ["Alice Tan"],
          "deadline": "20/11/2026",
          "subtasks": [
            {
              "subtask_id": "S001",
              "task": "Generate keys",
              "planned_date": "18/11/2026",
              "dependencies": []
            }
          ],
          "clarification_questions": [
            "Which server cluster needs updating?"
          ]
        }
      ],
      "bau_tasks": [
        {
          "task": "Weekly health check",
          "description": "Inspect logs and alerts",
          "owners": ["Bob Lim"],
          "frequency": "weekly",
          "start_date": "01/11/2026",
          "end_date": "30/11/2026",
          "clarification_questions": []
        }
      ],
      "important_information": [
        "Maintenance window on Sunday 2 AM"
      ]
    }
    ```
    """
    coordinator = HandoverCoordinator(llm_service=MockLLM(mock_response))
    result = coordinator.review_handover("Raw handover document text")

    assert result["success"] is True
    data = result["data"]

    # Verify Outstanding Tasks
    assert len(data["outstanding_tasks"]) == 1
    out_task = data["outstanding_tasks"][0]
    assert out_task["task"] == "Update server credentials"
    assert out_task["owners"] == ["Alice Tan"]
    assert out_task["deadline"] == "20/11/2026"
    assert out_task["clarification_questions"] == ["Which server cluster needs updating?"]
    assert len(out_task["subtasks"]) == 1
    assert out_task["subtasks"][0]["subtask_id"] == "S001"

    # Verify BAU Tasks
    assert len(data["bau_tasks"]) == 1
    bau_task = data["bau_tasks"][0]
    assert bau_task["task"] == "Weekly health check"
    assert bau_task["frequency"] == "weekly"
    assert bau_task["start_date"] == "01/11/2026"
    assert bau_task["end_date"] == "30/11/2026"
    assert bau_task["clarification_questions"] == []

    # Verify Important Information
    assert data["important_information"] == ["Maintenance window on Sunday 2 AM"]


def test_coordinator_handles_empty_content():
    coordinator = HandoverCoordinator(llm_service=MockLLM("{}"))
    result = coordinator.review_handover("   ")
    assert result["success"] is False
    assert "empty" in result["error_message"].lower()


def test_coordinator_repairs_faulty_json():
    # Single quotes, trailing commas, missing closing braces
    faulty_json = "{'outstanding_tasks': [{'task': 'Patch system', 'owners': ['Alice',], }], 'bau_tasks': [], 'important_information': []"
    coordinator = HandoverCoordinator(llm_service=MockLLM(faulty_json))
    result = coordinator.review_handover("Please review my notes")

    assert result["success"] is True
    assert result["data"]["outstanding_tasks"][0]["task"] == "Patch system"


def test_coordinator_handles_llm_runtime_error():
    mock_service = MagicMock(spec=LLMService)
    mock_service.generate.side_effect = RuntimeError("Rate limit exceeded")

    coordinator = HandoverCoordinator(llm_service=mock_service)
    result = coordinator.review_handover("Valid notes")

    assert result["success"] is False
    assert result["data"] is None
    assert "Rate limit exceeded" in result["error_message"]


def test_strip_clarification_questions_and_process_with_handover_manager():
    data_with_questions = {
        "outstanding_tasks": [
            {
                "task_id": "OUT-1",
                "task": "Deploy service",
                "description": "Production release",
                "owners": ["Alice"],
                "owner_ids": [],
                "deadline": "25/11/2026",
                "subtasks": [],
                "clarification_questions": ["What is the staging URL?"]
            }
        ],
        "bau_tasks": [
            {
                "task_id": "BAU-1",
                "task": "Monitor queue",
                "description": "Check RabbitMQ",
                "owners": ["Bob"],
                "owner_ids": [],
                "frequency": "weekly",
                "start_date": "01/11/2026",
                "end_date": None,
                "clarification_questions": ["Where is RabbitMQ hosted?"]
            }
        ],
        "important_information": ["Service password updated"]
    }

    # Strip questions
    cleaned_data = HandoverCoordinator.strip_clarification_questions(data_with_questions)

    # Verify clarification_questions were removed
    assert "clarification_questions" not in cleaned_data["outstanding_tasks"][0]
    assert "clarification_questions" not in cleaned_data["bau_tasks"][0]

    # Handover logic manager processes the cleaned data without error
    handover = Handover(cleaned_data)
    processed = handover.process()
    assert processed["status"] == "complete"
    assert len(processed["outstanding_tasks"]) == 1
    assert len(processed["bau_tasks"]) == 1
