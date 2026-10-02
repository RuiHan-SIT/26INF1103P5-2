import src.modules.logic_manager as logic_manager
import json

data = {
    "outstanding_tasks": [
        {
            "task": "Submit report",
            "description": "Submit monthly security report",
            "owners": ["John"],
            "deadline": "02/11/2026"
        },
        {
            "task": "Review alerts",
            "description": "Review outstanding security alerts",
            "owners": ["Mary"],
            "deadline": "15/10/2026"
        }
    ],
    "bau_tasks": [
        {
            "task": "Daily monitoring",
            "description": "Monitor security alerts",
            "owners": ["John"]
        }
    ],
    "important_information": [
        "System maintenance on Friday"
    ]
}

result = logic_manager.process_handover(data)

print(result)

result = logic_manager.process_handover(data)

with open("temp_result.json", "w") as file:
    json.dump(result, file, indent=4)
