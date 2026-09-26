import src.modules.logic_manager as logic_manager

handover_errors = {
    "outstanding_tasks": [
        {
            "task": "Complete security report",
            "description": "Prepare September report.",
            "owners": [],
            "deadline": ""
        },
        {
            "task": "Review access requests",
            "description": "",
            "owners": ["Sarah"],
            "deadline": "2026-02-30"
        }
    ],

    "bau_tasks": [
        {
            "task": "Review security alerts",
            "description": "Review new alerts.",
            "owners": ["John"]
        },
        {
            "task": "",
            "description": "",
            "owners": []
        }
    ],

    "important_information": [
        "Reports are stored in the shared drive."
    ]
}

print(logic_manager.validate_handover(handover_errors))