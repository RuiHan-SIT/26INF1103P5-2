from datetime import datetime

# Validate user's name
def validate_name(name): 
    if name.strip() == "":
        return False
    
    has_letter = False

    for char in name: 
        if char.isalpha():
            has_letter = True

    return has_letter

# Validate user's department
def validate_department(department): 
    if department.strip() == "":
        return False

    has_letter = False
    
    for char in department: 
        if char.isalpha():
            has_letter = True
    
    return has_letter

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
        errors.append("owners")
    
    if deadline.strip() == "":
        errors.append("missing_deadline")
    else:
        try:
            datetime.strptime(deadline, "%d/%m/%Y")
        except ValueError:
            errors.append("invalid_deadline")

    return errors

# Check required info for BAU tasks
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
        errors.append("owners")

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

    return errors

# Determine if handover needs re-prompt/clarifications
def get_handover_status(data, errors):
    outstanding_tasks = data["outstanding_tasks"]
    bau_tasks = data["bau_tasks"]

    if len(errors) != 0 or (len(outstanding_tasks) == 0 and len(bau_tasks) == 0):
        return "incomplete"
    else:
        return "complete"

# Get task deadline for sorting
def get_deadline(task):
    return task["deadline"]

# Sort outstanding tasks by earliest to latest deadline
def sort_outstanding_tasks(data):
    outstanding_tasks = data["outstanding_tasks"]

    sorted_tasks = sorted(outstanding_tasks, key=get_deadline)
    return sorted_tasks

# Format deadline as DD/MMM/YYYY
def format_deadline(deadline):
    date = datetime.strptime(deadline, "%d/%m/%Y")
    return date.strftime("%d %b %Y")