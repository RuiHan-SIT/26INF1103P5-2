import pytest
from pydantic import ValidationError
from model.handover_model import validate_handover                                                                                     

# ===========================================================================
# 1. Handover schema validation tests
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

