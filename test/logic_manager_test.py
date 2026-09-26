from src.modules.logic_manager import validate_outstanding_task, validate_bau_task

# Test 1 - All fields valid
task_outstanding_1 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "2026-10-05"
}

# Test 2 - Missing task name
task_outstanding_2 = {
    "task": "",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "2026-10-05"
}

# Test 3 - Task name contains only spaces
task_outstanding_3 = {
    "task": "   ",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "2026-10-05"
}

# Test 4 - Missing description
task_outstanding_4 = {
    "task": "Complete security report",
    "description": "",
    "owners": ["John"],
    "deadline": "2026-10-05"
}

# Test 5 - Description contains only spaces
task_outstanding_5 = {
    "task": "Complete security report",
    "description": "   ",
    "owners": ["John"],
    "deadline": "2026-10-05"
}

# Test 6 - No owners
task_outstanding_6 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": [],
    "deadline": "2026-10-05"
}

# Test 7 - Missing deadline
task_outstanding_7 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": ""
}

# Test 8 - Deadline contains only spaces
task_outstanding_8 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "   "
}

# Test 9 - Wrong date format
task_outstanding_9 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "05-10-2026"
}

# Test 10 - Invalid month
task_outstanding_10 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "2026-13-05"
}

# Test 11 - Invalid day
task_outstanding_11 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "2026-10-32"
}

# Test 12 - Invalid date (April only has 30 days)
task_outstanding_12 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "2026-04-31"
}

# Test 13 - Valid leap year
task_outstanding_13 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "2028-02-29"
}

# Test 14 - Invalid leap year
task_outstanding_14 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John"],
    "deadline": "2026-02-29"
}

# Test 15 - Multiple owners
task_outstanding_15 = {
    "task": "Complete security report",
    "description": "Prepare September report for management.",
    "owners": ["John", "Sarah", "Alex"],
    "deadline": "2026-12-31"
}


print("Test 1:", validate_outstanding_task(task_outstanding_1))
print("Test 2:", validate_outstanding_task(task_outstanding_2))
print("Test 3:", validate_outstanding_task(task_outstanding_3))
print("Test 4:", validate_outstanding_task(task_outstanding_4))
print("Test 5:", validate_outstanding_task(task_outstanding_5))
print("Test 6:", validate_outstanding_task(task_outstanding_6))
print("Test 7:", validate_outstanding_task(task_outstanding_7))
print("Test 8:", validate_outstanding_task(task_outstanding_8))
print("Test 9:", validate_outstanding_task(task_outstanding_9))
print("Test 10:", validate_outstanding_task(task_outstanding_10))
print("Test 11:", validate_outstanding_task(task_outstanding_11))
print("Test 12:", validate_outstanding_task(task_outstanding_12))
print("Test 13:", validate_outstanding_task(task_outstanding_13))
print("Test 14:", validate_outstanding_task(task_outstanding_14))
print("Test 15:", validate_outstanding_task(task_outstanding_15))

#===========================================================================
# BAU Task Tests

task_bau_1 = {
    "task": "Review security alerts",
    "description": "Review new alerts and escalate where required.",
    "owners": ["John"]
}

task_bau_2 = {
    "task": "",
    "description": "Review new alerts and escalate where required.",
    "owners": ["John"]
}

task_bau_3 = {
    "task": "Review security alerts",
    "description": "",
    "owners": ["John"]
}

task_bau_4 = {
    "task": "Review security alerts",
    "description": "Review new alerts and escalate where required.",
    "owners": []
}

task_bau_5 = {
    "task": "Review security alerts",
    "description": "Review new alerts and escalate where required.",
    "owners": ["John", "Sarah"]
}

print("BAU Test 1:", validate_bau_task(task_bau_1))
print("BAU Test 2:", validate_bau_task(task_bau_2))
print("BAU Test 3:", validate_bau_task(task_bau_3))
print("BAU Test 4:", validate_bau_task(task_bau_4))
print("BAU Test 5:", validate_bau_task(task_bau_5))