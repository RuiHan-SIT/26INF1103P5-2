
import sys
from pathlib import Path
import pytest

# Allow tests to import modules from src/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Project imports must come AFTER the src path setup
import main as app_main
from modules import input_handler, logic_manager







# ===========================================================================
# 1. File input integration test
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

