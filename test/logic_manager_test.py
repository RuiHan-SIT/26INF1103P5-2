import src.modules.logic_manager as logic_manager

# Get updated handover status function test 

data = {
    "outstanding_tasks": [
        {
            "task": "Complete report",
            "description": "Complete the monthly report",
            "owners": ["John"],
            "deadline": "20/2/2026"
        }
    ],
    "bau_tasks": [
        {
            "task": "Weekly report",
            "description": "Prepare weekly report",
            "owners": ["John"]
        }
    ]
}

errors = logic_manager.validate_handover(data)
print(errors)
print(logic_manager.get_handover_status(data, errors))