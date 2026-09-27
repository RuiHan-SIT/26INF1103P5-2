import src.modules.logic_manager as logic_manager

# Handover Status Tests

errors_1 = []
errors_2 = [
    {
        "type": "outstanding",
        "index": 1,
        "task": "Complete security report",
        "errors": ["owners"]
    }
]

print("Status Test 1:", logic_manager.get_handover_status(errors_1))
print("Status Test 2:", logic_manager.get_handover_status(errors_2))