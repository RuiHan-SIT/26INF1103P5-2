import pytest
from apps.schema import HandoverSchema, validate_and_normalize_handover


def test_handover_schema_assigns_default_task_ids_and_cleans_lists():
    raw_data = {
        "outstanding_tasks": [
            {
                "task": "  Migrate database  ",
                "description": "Upgrade to Postgres 16",
                "owners": ["  Alice ", "Bob  ", ""],
                "deadline": "25/11/2026",
                "clarification_questions": ["  Which server?  "]
            }
        ],
        "bau_tasks": [
            {
                "task": "Daily backup",
                "frequency": " DAILY ",
                "start_date": "01/11/2026",
                "end_date": "  ",
                "owners": ["Carol"]
            }
        ],
        "important_information": ["  System restart at midnight  "]
    }

    normalized = validate_and_normalize_handover(raw_data)

    # Outstanding task checks
    out_task = normalized["outstanding_tasks"][0]
    assert out_task["task_id"] == "OUT-1"
    assert out_task["task"] == "Migrate database"
    assert out_task["owners"] == ["Alice", "Bob"]
    assert out_task["clarification_questions"] == ["Which server?"]

    # BAU task checks
    bau_task = normalized["bau_tasks"][0]
    assert bau_task["task_id"] == "BAU-1"
    assert bau_task["frequency"] == "daily"
    assert bau_task["end_date"] is None
    assert bau_task["owners"] == ["Carol"]

    # Important information checks
    assert normalized["important_information"] == ["System restart at midnight"]


def test_handover_schema_preserves_existing_task_ids():
    raw_data = {
        "outstanding_tasks": [
            {"task_id": "CUSTOM-OUT", "task": "Task A"}
        ],
        "bau_tasks": [
            {"task_id": "CUSTOM-BAU", "task": "Task B"}
        ],
        "important_information": []
    }

    normalized = validate_and_normalize_handover(raw_data)
    assert normalized["outstanding_tasks"][0]["task_id"] == "CUSTOM-OUT"
    assert normalized["bau_tasks"][0]["task_id"] == "CUSTOM-BAU"


def test_handover_schema_flattens_dictionary_important_info():
    raw_data = {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": [
            {"alert": "High CPU load", "context": "Reported on node 2"}
        ]
    }

    normalized = validate_and_normalize_handover(raw_data)
    assert normalized["important_information"] == ["High CPU load - Reported on node 2"]
