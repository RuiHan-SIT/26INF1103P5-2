from utils.logger import logger
from pathlib import Path

# Anchor to the project root (../../ up from src/modules/) so the path
# works no matter which directory the program is launched from.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
handover_dir = BASE_DIR / "data" / "handovers"

def validate_txt_file(filename):
    # accept both str and Path, work with a Path internally
    path = Path(filename)

    # checks if the file is in the correct format
    if path.suffix.lower() != ".txt":
        raise ValueError(f"Invalid file type for '{filename}'. Expected a .txt file.")

    # checks if the file exists
    if not path.exists():
        raise FileNotFoundError(f"File not found: '{filename}'")

    # checks if the file is empty
    if path.stat().st_size == 0:
        raise ValueError(f"File is empty: '{filename}'")

    

def read_txt_file(filename: str):
    try:
        validate_txt_file(filename)

        with open(filename, 'r', encoding='utf-8') as file:
            handover_info = file.read()

        if not handover_info.strip():
            logger.error(f"File '{filename}' contains only whitespace or blank lines.")
            return None

        return handover_info

    except (FileNotFoundError, ValueError) as err:
        # Use logger.error for handled validation failures
        logger.error(f"Validation failed for '{filename}': {err}")
        return None

    except UnicodeDecodeError:
        # Use logger.exception to log the full decode stack trace
        logger.exception(f"Encoding error: '{filename}' could not be decoded as UTF-8.")
        return None


def sensitive_info(text): #function to check if there is any sensitive information in the file
    sensitive_keywords = ["password", "credit card", "bank account", "nric", "passport", "driver's license", "confidential", "secret", "private", "restricted"]
    text_lower = text.lower()

    for keyword in sensitive_keywords:
        if keyword in text_lower:
            print("Sensitive information detected. Please remove any sensitive information before proceeding.")
            return True

    return False
    
#function to get user details
def get_user_details(): 
    name = input("Enter your name: ") #employee name
    department = input("Enter your department: ") #employee department

    print("\n Are you:")
    print("1. Handing over work") #letting employee choose whether to handover or takeover
    print("2. Taking over work")

    role = input("Select an option: ") 

    if role == "1":
        handover_role = "Handing over"
    elif role == "2":
        handover_role = "Taking over"
    else:
        print("Invalid option.")
        return None

    return name, department, handover_role

def required_input(prompt): #this is to ensure manually added information for required fields
    while True:
        value = input(prompt).strip()

        if value == "":
            print("This field is required. Please enter a value.")
        else:
            return value

def get_handover_info(): #list of details for the handover task, kept the information in a dictionary format to allow more than one task to be recorded
    while True:
        task = required_input("Enter the task name:")
        description = required_input("Enter the task description: ")
        owner_input = required_input("Enter task owner(s), separated by commas: ")
        owners = [owner.strip() for owner in owner_input.split(",")]
        deadline = required_input("Enter deadline (DD/MM/YYYY):")
        comments = input("Enter any additional comments(optional):")

        text_check =(  # to double check sensitive information for manually entered data
            task + " "+
            description + " " +
            owner_input + " " +
            deadline + " " +
            comments
        )


        if sensitive_info(text_check):
            print("Please re-enter the task. \n")
        else:
            task_info = {
                "task": task,
                "description": description,
                "owners": owners,
                "deadline": deadline,
                "comments": comments
            }

        return task_info

def handover_input():  #allows user to enter more than one task at a time
    while True:
        print("\nEnter the information for handover: ")
        print("1. Enter the information manually")
        print("2. Load a .txt file")

        choice = input("Select an option: ")

        if choice == "1":
            tasks = []

            while True:
                task_info = get_handover_info()
                tasks.append(task_info)

                while True:
                    more = input(
                        "\nDo you want to add more tasks? (yes/no): "
                    ).lower()

                    if more == "yes" or more == "no":
                        break
                    else:
                        print("Invalid input. Please enter yes or no")

                if more == "no":
                    break

            return tasks

        elif choice == "2":
            filename = input("Enter the .txt filename: ")
            input_file = handover_dir / filename

            handover_info = read_txt_file(input_file)
            if handover_info is None:
                continue

            if sensitive_info(handover_info):
                continue

            return handover_info

        else:
            print("Invalid option. Please select 1 or 2.")

def main():   #mainflow
    user_details = get_user_details()

    if user_details is None:
        return

    name, department, handover_role = user_details

    if handover_role == "Handing over":
        handover_info = handover_input()

        if handover_info is None:
            return

        print("Input is successfully validated.")

        return name, department, handover_role, handover_info

    elif handover_role == "Taking over":
        print("No handover input required.")

        return name, department, handover_role
main()