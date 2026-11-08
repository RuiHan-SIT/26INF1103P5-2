import copy
from datetime import date, datetime, timedelta

from apps.handovers.logic_manager.bau_task import BAUTask
from apps.handovers.logic_manager.handover import Handover
from apps.handovers.logic_manager.employee_identity_matcher import EmployeeIdentityMatcher
from apps.handovers.logic_manager.outstanding_task import OutstandingTask
from apps.handovers.logic_manager.workload_validator import WorkloadValidator


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


def test_outstanding_defaults_and_bau_requires_frequency_and_start_date():
    deadline = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")
    outstanding = OutstandingTask("Report", "Prepare report", ["Alice"], deadline)
    bau = BAUTask("Logs", "Review logs", ["Alice"], "weekly", "01/11/2026")
    assert outstanding.to_dict()["task_id"] is None
    assert outstanding.to_dict()["owner_ids"] == []
    assert outstanding.to_dict()["subtasks"] == []
    assert bau.to_dict()["owner_ids"] == []
    assert bau.to_dict()["frequency"] == "weekly"
    assert bau.to_dict()["start_date"] == "01/11/2026"
    assert bau.to_dict()["end_date"] is None
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
    task = BAUTask("", "", [], "weekly", "01/11/2026")
    assert task.validate() == ["task", "description", "missing_owner(s)"]
    assert OutstandingTask("Report", "Prepare report", ["Alice"], "").validate() == ["missing_deadline"]
    past = (date.today() - timedelta(days=1)).strftime("%d/%m/%Y")
    assert OutstandingTask("Report", "Prepare report", ["Alice"], past).validate() == ["invalid_deadline"]


def test_empty_handover_is_still_incomplete():
    result = Handover({"outstanding_tasks": [], "bau_tasks": [], "important_information": []}).process()
    assert result == {"status": "incomplete", "errors": [{"type": "handover", "errors": ["no_tasks"]}]}

def test_bau_validation_accepts_valid_frequency_and_optional_end_date():
    task = BAUTask(
        "Review logs", "Check system logs", ["Alice"],
        frequency="Weekly", start_date="01/11/2020", end_date=None
    )
    assert task.validate() == []


def test_bau_validation_requires_frequency_and_start_date():
    task = BAUTask("Review logs", "Check system logs", ["Alice"], "", "")
    assert task.validate() == ["missing_frequency", "missing_start_date"]


def test_bau_validation_rejects_invalid_frequency_and_dates():
    task = BAUTask(
        "Review logs", "Check system logs", ["Alice"],
        frequency="Daily", start_date="31/02/2026", end_date="not a date"
    )
    assert task.validate() == [
        "invalid_frequency", "invalid_start_date", "invalid_end_date"
    ]


def test_bau_validation_rejects_end_date_before_start_date():
    task = BAUTask(
        "Review logs", "Check system logs", ["Alice"],
        frequency="monthly", start_date="10/11/2026", end_date="09/11/2026"
    )
    assert task.validate() == ["end_date_before_start_date"]





def test_outstanding_subtasks_accept_valid_dates_and_prior_dependencies():
    today = date.today()
    deadline = (today + timedelta(days=10)).strftime("%d/%m/%Y")
    first_date = (today + timedelta(days=2)).strftime("%d/%m/%Y")
    second_date = (today + timedelta(days=4)).strftime("%d/%m/%Y")
    subtasks = [
        {"subtask_id": "S001", "task": "Gather findings",
         "planned_date": first_date, "dependencies": []},
        {"subtask_id": "S002", "task": "Compile report",
         "planned_date": second_date, "dependencies": ["S001"]}
    ]
    task = OutstandingTask("Report", "Prepare report", ["Alice"], deadline, subtasks=subtasks)
    assert task.validate() == []


def test_outstanding_subtasks_reject_late_dates_and_invalid_dependencies():
    today = date.today()
    deadline = (today + timedelta(days=5)).strftime("%d/%m/%Y")
    late_date = (today + timedelta(days=6)).strftime("%d/%m/%Y")
    valid_date = (today + timedelta(days=2)).strftime("%d/%m/%Y")
    subtasks = [
        {"subtask_id": "S001", "task": "Gather findings",
         "planned_date": late_date, "dependencies": []},
        {"subtask_id": "S002", "task": "Compile report",
         "planned_date": valid_date, "dependencies": ["S003"]},
        {"subtask_id": "S003", "task": "Review report",
         "planned_date": valid_date, "dependencies": ["UNKNOWN"]}
    ]
    task = OutstandingTask("Report", "Prepare report", ["Alice"], deadline, subtasks=subtasks)
    assert task.validate() == [
        "subtask_1_planned_date_after_deadline",
        "subtask_2_invalid_dependency",
        "subtask_3_invalid_dependency"
    ]


def test_outstanding_subtasks_report_missing_fields_and_invalid_date():
    deadline = (date.today() + timedelta(days=5)).strftime("%d/%m/%Y")
    task = OutstandingTask(
        "Report", "Prepare report", ["Alice"], deadline,
        subtasks=[{"subtask_id": "S001", "task": "", "planned_date": "31/02/2026"}]
    )
    assert task.validate() == [
        "subtask_1_missing_task",
        "subtask_1_invalid_planned_date",
        "subtask_1_invalid_dependencies"
    ]


def test_dependency_cannot_be_planned_before_its_subtask():
    today = date.today()
    deadline = (today + timedelta(days=10)).strftime("%d/%m/%Y")
    earlier_work_date = (today + timedelta(days=3)).strftime("%d/%m/%Y")
    dependent_work_date = (today + timedelta(days=2)).strftime("%d/%m/%Y")
    subtasks = [
        {"subtask_id": "S001", "task": "Gather findings",
         "planned_date": earlier_work_date, "dependencies": []},
        {"subtask_id": "S002", "task": "Compile report",
         "planned_date": dependent_work_date, "dependencies": ["S001"]}
    ]
    task = OutstandingTask("Report", "Prepare report", ["Alice"], deadline, subtasks=subtasks)
    assert task.validate() == ["subtask_2_dependency_date_order"]


def test_dependent_subtasks_may_share_the_same_planned_date():
    today = date.today()
    deadline = (today + timedelta(days=10)).strftime("%d/%m/%Y")
    same_date = (today + timedelta(days=3)).strftime("%d/%m/%Y")
    subtasks = [
        {"subtask_id": "S001", "task": "Gather findings",
         "planned_date": same_date, "dependencies": []},
        {"subtask_id": "S002", "task": "Compile report",
         "planned_date": same_date, "dependencies": ["S001"]}
    ]
    task = OutstandingTask("Report", "Prepare report", ["Alice"], deadline, subtasks=subtasks)
    assert task.validate() == []


def test_subtask_cannot_be_completed_before_its_dependencies():
    subtasks = [
        {"subtask_id": "S001", "task": "Gather findings",
         "planned_date": "11/11/2026", "dependencies": []},
        {"subtask_id": "S002", "task": "Compile report",
         "planned_date": "12/11/2026", "dependencies": ["S001"]}
    ]
    task = OutstandingTask(
        "Report", "Prepare report", ["Alice"], "20/11/2026",
        subtasks=subtasks
    )
    assert task.can_complete_subtask("S001", []) is True
    assert task.can_complete_subtask("S002", []) is False
    assert task.can_complete_subtask("S002", ["S001"]) is True



def test_identity_match_ignores_name_capitalization_and_spaces():
    employees = [
        {"employee_id": "E001", "name": "Alice Tan", "department": "HR"}
    ]
    matcher = EmployeeIdentityMatcher(employees)

    result = matcher.match_owners(["alice  tan"])

    assert result == [{
        "owner_name": "alice  tan",
        "status": "confirmation_required",
                "match_level": "exact",
        "matches": [
            {"employee_id": "E001", "name": "Alice Tan", "department": "HR"}
        ]
    }]


def test_identity_match_returns_unmatched_owner_for_confirmation():
    matcher = EmployeeIdentityMatcher([
        {"employee_id": "E001", "name": "Alice Tan", "department": "HR"}
    ])

    result = matcher.match_owners(["Bob Lim"])

    assert result == [{
        "owner_name": "Bob Lim",
        "status": "unmatched",
                "match_level": None,
        "matches": []
    }]


def test_identity_match_returns_all_duplicate_name_candidates():
    employees = [
        {"employee_id": "E001", "name": "Alex Lee", "department": "HR"},
        {"employee_id": "E002", "name": "Alex Lee", "department": "IT"}
    ]
    matcher = EmployeeIdentityMatcher(employees)

    result = matcher.match_owners(["Alex Lee"])

    assert result[0]["status"] == "confirmation_required"
    assert result[0]["matches"] == employees


def test_identity_match_level_two_combines_name_parts():
    matcher = EmployeeIdentityMatcher([
        {"employee_id": "E001", "name": "Lim Ti Seng", "department": "HR"}
    ])

    result = matcher.match_owners(["tiseng"])

    assert result[0]["match_level"] == "components"
    assert result[0]["matches"][0]["employee_id"] == "E001"


def test_identity_match_level_two_allows_reordered_missing_parts():
    matcher = EmployeeIdentityMatcher([
        {"employee_id": "E001", "name": "Kit Isen Gom", "department": "HR"}
    ])

    result = matcher.match_owners(["Isen Kit"])

    assert result[0]["match_level"] == "components"
    assert result[0]["matches"][0]["employee_id"] == "E001"


def test_identity_match_level_three_suggests_fuzzy_match_with_score():
    matcher = EmployeeIdentityMatcher([
        {"employee_id": "E001", "name": "Lim Ti Seng", "department": "HR"}
    ])

    result = matcher.match_owners(["tisen"])

    assert result[0]["match_level"] == "fuzzy"
    assert result[0]["status"] == "confirmation_required"
    assert result[0]["matches"][0]["similarity"] >= 70


def test_workload_warns_after_four_items_across_handovers():
    handovers = [
        {"outstanding_tasks": [
            {"task": "First report", "owner_ids": ["E001"], "subtasks": [
                {"planned_date": "12/11/2026"},
                {"planned_date": "12/11/2026"}
            ]}
        ], "bau_tasks": []},
        {"outstanding_tasks": [
            {"task": "Second report", "owner_ids": ["E001"], "subtasks": [
                {"planned_date": "12/11/2026"},
                {"planned_date": "12/11/2026"},
                {"planned_date": "12/11/2026"}
            ]}
        ], "bau_tasks": []}
    ]

    warnings = WorkloadValidator().check_workload(
        handovers, "12/11/2026", "12/11/2026"
    )

    assert warnings == [{
        "type": "daily_workload_exceeded",
        "employee_id": "E001",
        "date": "12/11/2026",
        "count": 5,
        "limit": 4,
        "tasks": ["First report"] * 2 + ["Second report"] * 3
    }]


def test_workload_counts_bau_occurrences_and_skips_unscheduled_tasks():
    handovers = [{
        "outstanding_tasks": [
            {"task": "Unscheduled", "owner_ids": ["E001"], "subtasks": []}
        ],
        "bau_tasks": [
            {"task": "Weekly audit A", "owner_ids": ["E001"],
             "frequency": "weekly", "start_date": "01/11/2026",
             "end_date": None},
            {"task": "Weekly audit B", "owner_ids": ["E001"],
             "frequency": "weekly", "start_date": "01/11/2026",
             "end_date": None},
            {"task": "Weekly audit C", "owner_ids": ["E001"],
             "frequency": "weekly", "start_date": "01/11/2026",
             "end_date": None}
        ]
    }]

    warnings = WorkloadValidator(daily_limit=2).check_workload(
        handovers, "08/11/2026", "08/11/2026"
    )

    assert warnings[0]["count"] == 3
    assert warnings[0]["tasks"] == [
        "Weekly audit A", "Weekly audit B", "Weekly audit C"
    ]


def test_monthly_bau_uses_last_day_when_start_day_is_not_in_month():
    validator = WorkloadValidator()
    task = {
        "frequency": "monthly",
        "start_date": "31/01/2026",
        "end_date": None
    }

    dates = validator.get_bau_occurrence_dates(
        task, datetime(2026, 2, 1).date(), datetime(2026, 2, 28).date()
    )

    assert dates == [datetime(2026, 2, 28).date()]



def test_exactly_four_items_does_not_create_a_warning():
    handovers = [{
        "outstanding_tasks": [{
            "task": "Report", "owner_ids": ["E001"], "subtasks": [
                {"planned_date": "12/11/2026"},
                {"planned_date": "12/11/2026"},
                {"planned_date": "12/11/2026"},
                {"planned_date": "12/11/2026"}
            ]
        }],
        "bau_tasks": []
    }]

    warnings = WorkloadValidator().check_workload(
        handovers, "12/11/2026", "12/11/2026"
    )

    assert warnings == []


def test_yearly_bau_on_february_29_occurs_on_february_28_in_non_leap_year():
    validator = WorkloadValidator()
    task = {
        "frequency": "yearly",
        "start_date": "29/02/2024",
        "end_date": None
    }

    dates = validator.get_bau_occurrence_dates(
        task, datetime(2025, 2, 28).date(), datetime(2025, 2, 28).date()
    )

    assert dates == [datetime(2025, 2, 28).date()]
