import copy
from datetime import date, timedelta

from classes.logic_manager.bau_task import BAUTask
from classes.logic_manager.handover import Handover
from classes.logic_manager.outstanding_task import OutstandingTask


def test_bau_keeps_new_fields():
    task = BAUTask(
        "Review logs", "Check system logs", ["Alice Tan"],
        frequency="weekly", start_date="01/11/2026", end_date="30/11/2026",
        task_id="BAU-1", owner_ids=["EMP-1"]
    )
    assert task.to_dict() == {
        "task_id": "BAU-1", "task": "Review logs",
        "description": "Check system logs", "owners": ["Alice Tan"],
        "owner_ids": ["EMP-1"], "frequency": "weekly",
        "start_date": "01/11/2026", "end_date": "30/11/2026"
    }


def test_stage_one_defaults_and_old_constructor_calls():
    deadline = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")
    outstanding = OutstandingTask("Report", "Prepare report", ["Alice"], deadline)
    bau = BAUTask("Logs", "Review logs", ["Alice"])
    assert outstanding.to_dict()["task_id"] is None
    assert outstanding.to_dict()["owner_ids"] == []
    assert outstanding.to_dict()["subtasks"] == []
    assert bau.to_dict()["owner_ids"] == []
    assert bau.to_dict()["frequency"] == ""
    assert bau.to_dict()["start_date"] == ""
    assert bau.to_dict()["end_date"] == ""
    assert outstanding.validate() == []
    assert bau.validate() == []


def test_subtasks_and_owner_ids_are_independent_copies():
    deadline = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")
    subtasks = [{"task": "Draft", "owners": ["Alice"]}]
    owner_ids = ["EMP-1"]
    task = OutstandingTask(
        "Report", "Prepare report", ["Alice"], deadline,
        task_id="OUT-1", owner_ids=owner_ids, subtasks=subtasks
    )
    subtasks[0]["owners"].append("Bob")
    owner_ids.append("EMP-2")
    exported = task.to_dict()
    assert exported["owner_ids"] == ["EMP-1"]
    assert exported["subtasks"][0]["owners"] == ["Alice"]
    exported["subtasks"][0]["owners"].append("Carol")
    exported["owner_ids"].append("EMP-3")
    assert task.to_dict()["subtasks"][0]["owners"] == ["Alice"]
    assert task.to_dict()["owner_ids"] == ["EMP-1"]


def test_handover_keeps_new_fields_dates_and_sorting():
    earlier = (date.today() + timedelta(days=2)).strftime("%d/%m/%Y")
    later = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")
    data = {
        "outstanding_tasks": [
            {"task_id": "OUT-2", "task": "Later", "description": "Later work",
             "owners": ["Alice"], "owner_ids": [], "deadline": later, "subtasks": []},
            {"task_id": "OUT-1", "task": "Earlier", "description": "Earlier work",
             "owners": ["Bob"], "owner_ids": [], "deadline": earlier, "subtasks": []}
        ],
        "bau_tasks": [
            {"task_id": "BAU-1", "task": "Logs", "description": "Review logs",
             "owners": ["Alice"], "owner_ids": [], "frequency": "weekly",
             "start_date": "01/11/2026", "end_date": ""}
        ],
        "important_information": ["Maintenance window"]
    }
    original = copy.deepcopy(data)
    result = Handover(data).process()
    assert result["status"] == "complete"
    assert result["outstanding_tasks"][0] == data["outstanding_tasks"][1]
    assert result["outstanding_tasks"][1] == data["outstanding_tasks"][0]
    assert result["bau_tasks"] == data["bau_tasks"]
    assert data == original


def test_existing_required_field_checks_remain():
    task = BAUTask("", "", [])
    assert task.validate() == ["task", "description", "missing_owner(s)"]
    assert OutstandingTask("Report", "Prepare report", ["Alice"], "").validate() == ["missing_deadline"]
    past = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
    assert OutstandingTask("Report", "Prepare report", ["Alice"], past).validate() == ["invalid_deadline"]


def test_empty_handover_is_still_incomplete():
    result = Handover({"outstanding_tasks": [], "bau_tasks": [], "important_information": []}).process()
    assert result == {"status": "incomplete", "errors": [{"type": "handover", "errors": ["no_tasks"]}]}
