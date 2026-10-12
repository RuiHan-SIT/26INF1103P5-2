from datetime import date, timedelta
from modules import logic_manager
from conftest import make_outstanding_task, make_bau_task, FIXTURES_DIR

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
    assert logic_manager.validate_outstanding_task(task) == ["missing_owner(s)"]


def test_outstanding_task_missing_description():
    task = make_outstanding_task(description="")
    assert logic_manager.validate_outstanding_task(task) == ["description"]


def test_outstanding_task_missing_deadline():
    task = make_outstanding_task(deadline="")
    assert logic_manager.validate_outstanding_task(task) == ["missing_deadline"]


# ===========================================================================
# 3. BAU task validation tests
# ===========================================================================


def test_valid_bau_task_has_no_errors():
    task = make_bau_task()
    assert logic_manager.validate_bau_task(task) == []


def test_bau_task_missing_owner():
    task = make_bau_task(owners=[])
    assert logic_manager.validate_bau_task(task) == ["missing_owner(s)"]


def test_bau_task_missing_description():
    task = make_bau_task(description="")
    assert logic_manager.validate_bau_task(task) == ["description"]

# ===========================================================================
# 4. Handover processing tests with hardcoded sample AI responses
# ===========================================================================

def test_empty_handover_is_incomplete():
    hardcoded_ai_response = {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [],
        }
    result = logic_manager.process_handover(hardcoded_ai_response)
    assert result["status"] == "incomplete"
    assert result["errors"][0]["errors"] == ["no_tasks"]

def test_valid_handover_is_complete():
    hardcoded_ai_response = {
        "outstanding_tasks": [make_outstanding_task()],
        "bau_tasks": [make_bau_task()],
        "important_information": [],
        }
    result = logic_manager.process_handover(hardcoded_ai_response)
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
    hardcoded_ai_response = {
        "outstanding_tasks": [later, earlier],
        "bau_tasks": [],
        "important_information": [],
        }
    result = logic_manager.process_handover(hardcoded_ai_response)
    assert result["status"] == "complete"
    assert result["outstanding_tasks"][0]["task"] == "Earlier task"
    assert result["outstanding_tasks"][1]["task"] == "Later task"

def test_deadline_is_formatted_in_output():
    deadline = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")
    hardcoded_ai_response = {
        "outstanding_tasks": [make_outstanding_task(deadline=deadline)],
        "bau_tasks": [],
        "important_information": [],
        }
    result = logic_manager.process_handover(hardcoded_ai_response)
    expected = date.today() + timedelta(days=7)
    expected_format = expected.strftime("%d %b %Y")
    assert result["outstanding_tasks"][0]["deadline"] == expected_format

def test_valid_handover_fixture_with_hardcoded_response():
    """Verify core logic handles realistic hardcoded sample AI responses without calling Gemini."""
    hardcoded_ai_response = {
        "outstanding_tasks": [
            {
                "task": "Complete website migration testing",
                "description": "Test all website functions before deployment.",
                "owners": ["Sarah Lim"],
                "deadline": "15/10/2026",
            },
            {
                "task": "Prepare deployment documentation",
                "description": "Document the deployment procedure and rollback steps.",
                "owners": ["Daniel Lee"],
                "deadline": "17/10/2026",
            },
        ],
        "bau_tasks": [],
        "important_information": [],
        }

    result = logic_manager.process_handover(hardcoded_ai_response)
    assert result["status"] == "complete"
    assert len(result["outstanding_tasks"]) == 2
    assert (
        result["outstanding_tasks"][0]["task"]
        == "Complete website migration testing"
        )
