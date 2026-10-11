
import sys
from pathlib import Path
from datetime import date, timedelta

import pytest
from pydantic import ValidationError
from src.modules import output

# Allow tests to import modules from src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Project imports must come AFTER the src path setup
import main as app_main
from modules import gemini_router, input_handler, logic_manager
from model.handover_model import validate_handover


# ===========================================================================
# Helper functions
# ===========================================================================

def make_outstanding_task(
    task="Test task",
    description="Test description",
    owners=None,
    deadline=None,
):
    """Create sample outstanding task data for testing."""
    if owners is None:
        owners = ["Alex"]

    if deadline is None:
        deadline = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")

    return {
        "task": task,
        "description": description,
        "owners": owners,
        "deadline": deadline,
    }


def make_bau_task(
    task="Routine task",
    description="Routine description",
    owners=None,
):
    """Create sample BAU task data for testing."""
    if owners is None:
        owners = ["Alex"]

    return {
        "task": task,
        "description": description,
        "owners": owners,
    }


# ===========================================================================
# 1. Deadline validation tests
# ===========================================================================

def test_valid_future_deadline():
    deadline = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")
    assert logic_manager.validate_deadline(deadline) is True


def test_past_deadline_is_invalid():
    deadline = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
    assert logic_manager.validate_deadline(deadline) is False


def test_wrong_deadline_format_is_invalid():
    assert logic_manager.validate_deadline("2026-10-15") is False


def test_empty_deadline_is_invalid():
    assert logic_manager.validate_deadline("") is False


# ===========================================================================
# 2. Outstanding task validation tests
# ===========================================================================

def test_valid_outstanding_task_has_no_errors():
    task = make_outstanding_task()
    assert logic_manager.validate_outstanding_task(task) == []


def test_outstanding_task_missing_owner():
    task = make_outstanding_task(owners=[])
    assert logic_manager.validate_outstanding_task(task) == [
        "missing_owner(s)"
    ]


def test_outstanding_task_missing_description():
    task = make_outstanding_task(description="")
    assert logic_manager.validate_outstanding_task(task) == [
        "description"
    ]


def test_outstanding_task_missing_deadline():
    task = make_outstanding_task(deadline="")
    assert logic_manager.validate_outstanding_task(task) == [
        "missing_deadline"
    ]


# ===========================================================================
# 3. BAU task validation tests
# ===========================================================================

def test_valid_bau_task_has_no_errors():
    task = make_bau_task()
    assert logic_manager.validate_bau_task(task) == []


def test_bau_task_missing_owner():
    task = make_bau_task(owners=[])
    assert logic_manager.validate_bau_task(task) == [
        "missing_owner(s)"
    ]


def test_bau_task_missing_description():
    task = make_bau_task(description="")
    assert logic_manager.validate_bau_task(task) == [
        "description"
    ]


# ===========================================================================
# 4. Handover processing tests
# ===========================================================================

def test_empty_handover_is_incomplete():
    data = {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [],
    }

    result = logic_manager.process_handover(data)

    assert result["status"] == "incomplete"
    assert result["errors"][0]["errors"] == ["no_tasks"]


def test_valid_handover_is_complete():
    data = {
        "outstanding_tasks": [make_outstanding_task()],
        "bau_tasks": [make_bau_task()],
        "important_information": [],
    }

    result = logic_manager.process_handover(data)

    assert result["status"] == "complete"
    assert "errors" not in result
    assert len(result["outstanding_tasks"]) == 1


def test_outstanding_tasks_are_sorted_by_deadline():
    later = make_outstanding_task(
        task="Later task",
        deadline=(date.today() + timedelta(days=10)).strftime("%d/%m/%Y"),
    )
    earlier = make_outstanding_task(
        task="Earlier task",
        deadline=(date.today() + timedelta(days=2)).strftime("%d/%m/%Y"),
    )

    data = {
        "outstanding_tasks": [later, earlier],
        "bau_tasks": [],
        "important_information": [],
    }

    result = logic_manager.process_handover(data)

    assert result["status"] == "complete"
    assert result["outstanding_tasks"][0]["task"] == "Earlier task"
    assert result["outstanding_tasks"][1]["task"] == "Later task"


def test_deadline_is_formatted_in_output():
    deadline = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")

    data = {
        "outstanding_tasks": [make_outstanding_task(deadline=deadline)],
        "bau_tasks": [],
        "important_information": [],
    }

    result = logic_manager.process_handover(data)

    expected = date.today() + timedelta(days=7)
    expected_format = expected.strftime("%d %b %Y")

    assert result["outstanding_tasks"][0]["deadline"] == expected_format


def test_valid_handover_fixture_with_hardcoded_response():
    """Use a real handover fixture without calling Gemini."""

    handover_path = FIXTURES_DIR / "valid_handover.txt"
    handover_text = handover_path.read_text(encoding="utf-8")

    assert "Complete website migration testing" in handover_text
    assert "Prepare deployment documentation" in handover_text

    fake_ai_response = {
        "outstanding_tasks": [
            {
                "task": "Complete website migration testing",
                "description": "Test all website functions before deployment.",
                "owners": ["Sarah Lim"],
                "deadline": "15/10/2026",
            },
            {
                "task": "Prepare deployment documentation",
                "description": (
                    "Document the deployment procedure and rollback steps."
                ),
                "owners": ["Daniel Lee"],
                "deadline": "17/10/2026",
            },
        ],
        "bau_tasks": [],
        "important_information": [],
    }

    result = logic_manager.process_handover(fake_ai_response)

    assert result["status"] == "complete"
    assert len(result["outstanding_tasks"]) == 2
    assert result["outstanding_tasks"][0]["task"] == (
        "Complete website migration testing"
    )


# ===========================================================================
# 5. Gemini response JSON cleaning tests
# ===========================================================================

def test_clean_llm_json_rejects_response_without_json():
    with pytest.raises(ValueError, match="No JSON object found"):
        gemini_router.clean_llm_json(
            "The AI could not generate a response."
        )


def test_clean_llm_json_rejects_empty_response():
    with pytest.raises(ValueError, match="empty or null response"):
        gemini_router.clean_llm_json("")


def test_clean_llm_json_removes_markdown_code_fences():
    raw_response = '''```json
    {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": []
    }
    ```'''

    result = gemini_router.clean_llm_json(raw_response)

    assert result == {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [],
    }


def test_clean_llm_json_rejects_whitespace_response():
    with pytest.raises(ValueError, match="empty or null response"):
        gemini_router.clean_llm_json("   \n\t   ")


# ===========================================================================
# 6. Handover schema validation tests
# ===========================================================================

def test_validate_handover_rejects_missing_required_task_field():
    data = {
        "outstanding_tasks": [
            {
                "description": "Test website before deployment.",
                "owners": ["Sarah Lim"],
                "deadline": "15/10/2026",
            }
        ],
        "bau_tasks": [],
        "important_information": [],
    }

    with pytest.raises(ValidationError):
        validate_handover(data)


def test_validate_handover_rejects_missing_bau_task_field():
    data = {
        "outstanding_tasks": [],
        "bau_tasks": [
            {
                "description": "Review routine system logs.",
                "owners": ["Alex Tan"],
            }
        ],
        "important_information": [],
    }

    with pytest.raises(ValidationError):
        validate_handover(data)


def test_validate_handover_normalizes_important_info_without_alert():
    data = {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [
            {
                "context": "Deployment is scheduled for tomorrow.",
            }
        ],
    }

    result = validate_handover(data)

    assert result["important_information"] == [
        "Deployment is scheduled for tomorrow."
    ]


def test_validate_handover_rejects_wrong_owners_data_type():
    data = {
        "outstanding_tasks": [
            {
                "task": "Complete website testing",
                "description": "Test all website functions.",
                "owners": 123,
                "deadline": "15/10/2026",
            }
        ],
        "bau_tasks": [],
        "important_information": [],
    }

    with pytest.raises(ValidationError):
        validate_handover(data)


def test_validate_handover_rejects_wrong_task_data_type():
    data = {
        "outstanding_tasks": [
            {
                "task": 12345,
                "description": "Test all website functions.",
                "owners": ["Sarah Lim"],
                "deadline": "15/10/2026",
            }
        ],
        "bau_tasks": [],
        "important_information": [],
    }

    with pytest.raises(ValidationError):
        validate_handover(data)


def test_validate_handover_ignores_unexpected_task_field():
    data = {
        "outstanding_tasks": [
            {
                "task": "Complete website testing",
                "description": "Test all website functions.",
                "owners": ["Sarah Lim"],
                "deadline": "15/10/2026",
                "unexpected_field": "This field is not in the schema",
            }
        ],
        "bau_tasks": [],
        "important_information": [],
    }

    result = validate_handover(data)

    assert result["outstanding_tasks"][0]["task"] == (
        "Complete website testing"
    )
    assert "unexpected_field" not in result["outstanding_tasks"][0]


# ===========================================================================
# 7. Mocked Gemini API test
# ===========================================================================

def test_send_to_llm_uses_mocked_gemini_api(monkeypatch):
    """Verify send_to_llm uses a mock instead of the real Gemini API."""

    fake_response = type(
        "FakeResponse",
        (),
        {
            "text": (
                '{"outstanding_tasks": [], '
                '"bau_tasks": [], '
                '"important_information": []}'
            )
        },
    )()

    def fake_generate_content(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(
        gemini_router.client.models,
        "generate_content",
        fake_generate_content,
    )

    result = gemini_router.send_to_llm("Test handover input")

    assert result == {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [],
    }


# ===========================================================================
# 8. File input integration test
# ===========================================================================

def test_handover_file_with_mocked_ai(monkeypatch):
    """Read a real handover file and test core logic without Gemini."""

    # Use the test fixture directory as the handover input directory.
    monkeypatch.setattr(
        input_handler,
        "handover_dir",
        FIXTURES_DIR,
    )

    # Simulate the user entering a filename in the application.
    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": "file:valid_handover.txt",
    )

    # Hardcoded AI response: no live API call is made.
    fake_ai_response = {
        "outstanding_tasks": [
            {
                "task": "Complete website testing",
                "description": "Test the login module.",
                "owners": ["Sarah Lim"],
                "deadline": "15/10/2026",
            }
        ],
        "bau_tasks": [
            {
                "task": "Review system logs",
                "description": "Review routine system logs.",
                "owners": ["Alex Tan"],
            }
        ],
        "important_information": [
            "Deployment maintenance is scheduled for next week."
        ],
    }

    received_inputs = []

    def fake_send_to_llm(text):
        received_inputs.append(text)
        return fake_ai_response

    # Replace the AI function used by main.py.
    monkeypatch.setattr(
        app_main,
        "send_to_llm",
        fake_send_to_llm,
    )

    # Run the actual file-input and handover-data flow.
    handover_data = app_main.get_handover_data()

    # Confirm the file contents reached the mocked AI function.
    expected_text = (
        FIXTURES_DIR / "valid_handover.txt"
    ).read_text(encoding="utf-8")

    assert received_inputs == [expected_text]

    # Run the actual core logic against the hardcoded response.
    result = logic_manager.process_handover(handover_data)

    assert result["status"] == "complete"
    assert len(result["outstanding_tasks"]) == 1
    assert (
        result["outstanding_tasks"][0]["task"]
        == "Complete website testing"
    )


def test_summary_saving_failure_is_handled(monkeypatch, tmp_path, capsys):
    # Simulate a file-saving failure
    def raise_os_error(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(output.os, "makedirs", raise_os_error)

    result = {
        "status": "Handover Complete",
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [],
    }

    user_details = {
        "name": "Test User",
        "employee_id": "TEST001",
    }

    # Attempt to save the summary
    saved_path = output.generate_summary_txt(
        result,
        user_details,
        output_dir=str(tmp_path),
    )

    # Verify the failure is handled correctly
    captured = capsys.readouterr()

    assert saved_path is None
    assert "[Error] Could not save summary file" in captured.out
    assert "Permission denied" in captured.out

def test_send_to_llm_handles_connection_failure(monkeypatch):
    # Simulate a network connection failure without calling the real API
    def raise_connection_error(*args, **kwargs):
        raise ConnectionError("Simulated network failure")

    monkeypatch.setattr(
        gemini_router.client.models,
        "generate_content",
        raise_connection_error,
    )

    # Call the function under test
    result = gemini_router.send_to_llm("Test handover input")

    # Verify the connection error is handled
    assert result["success"] is False
    assert result["data"] is None
    assert "Network timeout" in result["error_message"]
    assert "internet connection" in result["error_message"]


def test_read_txt_file_handles_missing_file(tmp_path):
    from src.modules import input_handler

    missing_file = tmp_path / "missing_handover.txt"

    result = input_handler.read_txt_file(missing_file)

    assert result is None


def test_read_txt_file_handles_invalid_utf8(tmp_path):
    from src.modules import input_handler

    # Create a file containing invalid UTF-8 bytes
    invalid_file = tmp_path / "invalid_encoding.txt"
    invalid_file.write_bytes(b"\xff\xfe\xfa")

    result = input_handler.read_txt_file(invalid_file)

    assert result is None


def test_clean_llm_json_repairs_malformed_json():
    from src.modules.gemini_router import clean_llm_json

    # Simulate JSON with a missing comma
    malformed_response = '{"status": "complete" "important_information": []}'

    result = clean_llm_json(malformed_response)

    assert isinstance(result, dict)
    assert result["status"] == "complete"
    assert result["important_information"] == []


def test_validate_name_rejects_empty_or_non_alphabetic_input():
    from src.modules.input_handler import validate_name

    assert validate_name("") is False
    assert validate_name("   ") is False
    assert validate_name("123456") is False


def test_validate_name_accepts_alphabetic_input():
    from src.modules.input_handler import validate_name

    assert validate_name("Alex") is True
    assert validate_name("Alex Tan") is True


def test_validate_department_rejects_empty_or_non_alphabetic_input():
    from src.modules.input_handler import validate_department

    assert validate_department("") is False
    assert validate_department("123456") is False


def test_validate_employee_id_requires_seven_digits():
    from src.modules.input_handler import validate_employee_id

    assert validate_employee_id("1234567") is True
    assert validate_employee_id("123456") is False
    assert validate_employee_id("12345678") is False
    assert validate_employee_id("ABC1234") is False
    assert validate_employee_id("1234 67") is False


def test_validate_user_input_detects_password_keyword(capsys):
    from src.modules.input_handler import validate_user_input

    result = validate_user_input(
        "The system password is example123"
    )

    captured = capsys.readouterr()

    assert result is True
    assert "Sensitive information detected" in captured.out
    assert "password" in captured.out