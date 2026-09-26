from src.modules.logic_manager import (
    validate_outstanding_task,
    validate_bau_task,
    validate_handover
)

handover_1 = {
    "outstanding_tasks": [
        {
            "task": "Complete security report",
            "description": "Prepare September report.",
            "owners": ["John"],
            "deadline": "2026-10-05"
        },
        {
            "task": "Review access requests",
            "description": "Review pending requests.",
            "owners": ["Sarah"],
            "deadline": "2026-10-10"
        }
    ],

    "bau_tasks": [
        {
            "task": "Review security alerts",
            "description": "Review new alerts.",
            "owners": ["John"]
        },
        {
            "task": "Check daily reports",
            "description": "Check reports for issues.",
            "owners": ["Sarah"]
        }
    ],

    "important_information": [
        "Reports are stored in the shared drive."
    ]
}

print("Handover Test 1:", validate_handover(handover_1))

handover_2 = {
    "outstanding_tasks": [
        {
            "task": "Complete security report",
            "description": "Prepare September report.",
            "owners": ["John"],
            "deadline": "2026-10-05"
        },
        {
            "task": "Review access requests",
            "description": "Review pending requests.",
            "owners": [],
            "deadline": "2026-10-10"
        }
    ],

    "bau_tasks": [
        {
            "task": "Review security alerts",
            "description": "Review new alerts.",
            "owners": ["John"]
        }
    ],

    "important_information": [
        "Reports are stored in the shared drive."
    ]
}

print("Handover Test 2:", validate_handover(handover_2))


handover_3 = {
    "outstanding_tasks": [
        {
            "task": "Complete security report",
            "description": "Prepare September report.",
            "owners": ["John"],
            "deadline": "2026-10-05"
        },
        {
            "task": "Review access requests",
            "description": "Review pending requests.",
            "owners": ["Sarah"],
            "deadline": "2026-10-10"
        }
    ],

    "bau_tasks": [
        {
            "task": "Review security alerts",
            "description": "Review new alerts.",
            "owners": ["John"]
        },
        {
            "task": "Check daily reports",
            "description": "",
            "owners": ["Sarah"]
        }
    ],

    "important_information": [
        "Reports are stored in the shared drive."
    ]
}

print("Handover Test 3:", validate_handover(handover_3))

handover_4 = {
    "outstanding_tasks": [],
    "bau_tasks": [
        {
            "task": "Review security alerts",
            "description": "Review new alerts.",
            "owners": ["John"]
        }
    ],
    "important_information": [
        "Reports are stored in the shared drive."
    ]
}

print("Handover Test 4:", validate_handover(handover_4))

handover_5 = {
    "outstanding_tasks": [
        {
            "task": "Complete security report",
            "description": "Prepare September report.",
            "owners": ["John"],
            "deadline": "2026-10-05"
        },
        {
            "task": "Review access requests",
            "description": "Review pending requests.",
            "owners": ["Sarah"],
            "deadline": "2026-10-10"
        }
    ],

    "bau_tasks": [],

    "important_information": [
        "Reports are stored in the shared drive."
    ]
}

print("Handover Test 5:", validate_handover(handover_5))