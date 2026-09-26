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
    task_name = task["task"]
    description = task["description"]
    owners = task["owners"]
    deadline = task["deadline"]

    if task_name.strip() == "":
        return False
    
    if description.strip() == "":
        return False
    
    if len(owners) == 0:
        return False
    
    if deadline.strip() == "":
        return False

    try:
        datetime.strptime(deadline, "%Y-%m-%d")
    except ValueError:
        return False

    return True

def validate_bau_task(task):
    task_name = task["task"]
    description = task["description"]
    owners = task["owners"]

    if task_name.strip() == "":
        return False
        
    if description.strip() == "":
        return False
        
    if len(owners) == 0:
        return False

    return True


