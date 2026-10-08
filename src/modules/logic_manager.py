from datetime import datetime

# Check required info in outstanding tasks
def validate_outstanding_task(task): 
    errors = []

    task_name = task["task"]
    description = task["description"]
    owners = task["owners"]
    deadline = task["deadline"]

    if task_name.strip() == "":
        errors.append("task")
    
    if description.strip() == "":
        errors.append("description")
    
    if len(owners) == 0:
        errors.append("missing_owner(s)")
    
    if deadline.strip() == "":
        errors.append("missing_deadline")
    else:
        try:
            datetime.strptime(deadline, "%d/%m/%Y")
        except ValueError:
            errors.append("invalid_deadline")

    return errors

# Check required info for BAU tasks and return all errors 
def validate_bau_task(task): 
    errors = []

    task_name = task["task"]
    description = task["description"]
    owners = task["owners"]

    if task_name.strip() == "":
        errors.append("task")
        
    if description.strip() == "":
        errors.append("description")
        
    if len(owners) == 0:
        errors.append("missing_owner(s)")

    return errors

# Check all tasks and collect errors 
def validate_handover(data):
    errors = []

    for index, task in enumerate(data["outstanding_tasks"], start=1):
        task_errors = validate_outstanding_task(task)

        if len(task_errors) > 0:
            errors.append({
                "type": "outstanding",
                "index": index,
                "task": task["task"],
                "errors": task_errors
            })

    for index, task in enumerate(data["bau_tasks"], start=1):
        task_errors = validate_bau_task(task)

        if len(task_errors) > 0:
            errors.append({
                "type": "bau",
                "index": index,
                "task": task["task"],
                "errors": task_errors
            })

    if len(data["outstanding_tasks"]) == 0 and len(data["bau_tasks"]) == 0:
        errors.append({
            "type": "handover",
            "errors": ["no_tasks"]
        })

    return errors

# Determine if handover needs re-prompt/clarifications
# Returns a status of "complete" or "incomplete"
def get_handover_status(data, errors):
    outstanding_tasks = data["outstanding_tasks"]
    bau_tasks = data["bau_tasks"]

    if len(errors) != 0 or (len(outstanding_tasks) == 0 and len(bau_tasks) == 0):
        return "incomplete" 
    else:
        return "complete"

# Get task deadline for sorting
def get_deadline(task):
    return datetime.strptime(task["deadline"], "%d/%m/%Y")

# Sort outstanding tasks by earliest to latest deadline
def sort_outstanding_tasks(data):
    outstanding_tasks = data["outstanding_tasks"]

    sorted_tasks = sorted(outstanding_tasks, key=get_deadline)
    return sorted_tasks

# Format deadline as DD/MMM/YYYY
def format_deadline(deadline):
    date = datetime.strptime(deadline, "%d/%m/%Y")
    return date.strftime("%d %b %Y")

# Return completed handover data
def process_handover(data):
    errors = validate_handover(data)
    status = get_handover_status(data, errors)

    if status == "incomplete":
        return {
            "status": status,
            "errors": errors
        }

    sorted_tasks = sort_outstanding_tasks(data)

    for task in sorted_tasks:
        task["deadline"] = format_deadline(task["deadline"])

    return {
    "status": status,
    "outstanding_tasks": sorted_tasks,
    "bau_tasks": data["bau_tasks"],
    "important_information": data["important_information"]
    }
