from datetime import datetime

def validate_name(name):
    if name.strip() == "":
        return False
    
    has_letter = False

    for char in name: 
        if char.isalpha():
            has_letter = True

    return has_letter

def validate_department(department):
    if department.strip() == "":
        return False

    has_letter = False
    
    for char in department: 
        if char.isalpha():
            has_letter = True
    
    return has_letter

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
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            errors.append("invalid_deadline")

    return errors

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

