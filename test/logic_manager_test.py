import src.modules.logic_manager as logic_manager

# Deadline Sorting Test

sorting_test = {
    "outstanding_tasks": [
        {
            "task": "Task A",
            "description": "Test",
            "owners": ["John"],
            "deadline": "2026-12-20"
        },
        {
            "task": "Task B",
            "description": "Test",
            "owners": ["Sarah"],
            "deadline": "2026-09-30"
        },
        {
            "task": "Task C",
            "description": "Test",
            "owners": ["Alex"],
            "deadline": "2026-10-15"
        },
        {
            "task": "Task D",
            "description": "Test",
            "owners": ["John"],
            "deadline": "2027-01-05"
        }
    ],
    "bau_tasks": [],
    "important_information": []
}

sorted_tasks = logic_manager.sort_outstanding_tasks(sorting_test)

for task in sorted_tasks:
    formatted_deadline = logic_manager.format_deadline(task["deadline"])
    task["deadline"] = formatted_deadline
    
    print(task)