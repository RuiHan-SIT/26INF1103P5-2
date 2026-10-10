from utils.logger import logger
from pathlib import Path
import scrubadub
from datetime import datetime
import re
# Build the Scrubber once and reuse it across calls (construction is not free).
_scrubber = scrubadub.Scrubber()
_scrubber.remove_detector('phone')

# Anchor to the project root (../../ up from src/modules/) so the path
# works no matter which directory the program is launched from.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
handover_dir = BASE_DIR / "data" / "handovers"


# ===========================================================================
# Helper Functions 
# Validate file
# 1) Check File Size, Check if file exists and Check if its a txt file
# ===========================================================================
# accept both str and Path, work with a Path internally
def validate_file(filename, max_bytes: int = 5 * 1024 * 1024):    
    path = Path(filename)

    # checks if the file is in the correct format
    if path.suffix.lower() != ".txt":
        raise ValueError(f"Invalid file type for '{filename}'. Expected a .txt file.")

    # checks if the file exists
    if not path.exists():
        raise FileNotFoundError(f"File not found: '{filename}'")

    # checks if the file is empty
    file_size = path.stat().st_size
    if file_size == 0:
        raise ValueError(f"File is empty: '{filename}'")

    # checks if the file is abnormally large
    if file_size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"File '{filename}' exceeds maximum allowed size "
            f"({actual_mb:.2f} MB > {max_mb:.2f} MB limit)."
        )
# ===========================================================================
# Helper Functions 
# Literally reads txt file.
# ===========================================================================
def read_txt_file(filename: str):
    try:
        validate_file(filename)

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
    
# ===========================================================================
# Helper Functions 
# Validate user input with scrubdud lib and regex
# ===========================================================================

def validate_user_input(text: str):  
    # scrubadub detects structured PII: emails, phone numbers, credit cards, etc.
    detected_types = {filth.type for filth in _scrubber.iter_filth(text)}

    # keyword check for domain-sensitive words scrubadub does not model as PII
    sensitive_keywords = [
        "password", "passport",
    ]
    
    sensitive_patterns ={
    "NRIC/FIN": r"\b[STFG]\d{7}[A-Z]$\b",
    "Passport": r"\b[E]\d{7}[A-Z]\b",
    }

    text_lower = text.lower()
    for keyword in sensitive_keywords:
        if keyword in text_lower:
            detected_types.add(keyword)

    for label, pattern in sensitive_patterns.items():
        if re.search(pattern, text):
            detected_types.add(label)

    if detected_types:
        print(
            "Sensitive information detected: "
            f"{', '.join(sorted(detected_types))}. "
            "Please remove any sensitive information before proceeding."
        )
        return True

    return False


def has_alphabetic_char(text: str) -> bool:                                                                                                                                          
    """Checks if a string is non-empty and contains at least one letter."""                                                                                                          
    return bool(text.strip()) and any(char.isalpha() for char in text) 

def validate_name(name: str) -> bool:                                                                                                                                    
    return has_alphabetic_char(name)
    
def validate_department(department: str) -> bool:                                                                                                                                    
    return has_alphabetic_char(department)                                                                                                                                           
                                                                                                                                                                                         
def validate_employee_id(employee_id: str) -> bool:                                                                                                                                  
    return len(employee_id) == 7 and employee_id.isdigit()



def required_input(prompt): #this is to ensure manually added information for required fields
    while True:
        value = input(prompt).strip()

        if value == "":
            print("This field is required. Please enter a value.")
        else:
            return value

def handover_from_file(filename):
    #Read and validate a handover .txt file by name (looked up in handover_dir).
    #returns the file text if valid and clean, otherwise None so the caller can
    #decide how to proceed (e.g. re-prompt).

    input_file = (handover_dir / filename).resolve()
    if not input_file.is_relative_to(handover_dir.resolve()):
        print("Invalid file path. Please provide a valid filename within the handover directory.")
        return None

    handover_info = read_txt_file(input_file)
    if handover_info is None:
        return None

    if validate_user_input(handover_info):
        return None

    return handover_info

def get_user_details(): #function to get user details
    while True: #get and validate user name
        name = required_input("Enter your name: ") #employee name

        if validate_name(name):
            break
        else:
            print("Invalid name. Please enter a valid name containing at least one letter.")
    while True: #get and validate user department
        department = required_input("Enter your department: ") #employee department

        if validate_department(department):
            break
        else:
            print("Invalid department. Please enter a valid department containing at least one letter.")  
    while True: #get and validate user employee ID
        employee_id = required_input("Enter your employee ID: ") #employee ID

        if validate_employee_id(employee_id):
            break
        else:
            print("Invalid employee ID. Please enter a valid 7-digit employee ID.")

    submission_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S") #get current date and time
    print("\nAre you:")
    print("1. Handing over work")
    print("2. Taking over work")

    while True:
        role = required_input("\nSelect an option: ") 

        if role == "1":

            return {
                "name": name,
                "department": department,
                "employee_id": employee_id,
                "date":submission_date,
                "role": "Handing over"
            }
        elif role == "2":
            while True:
                previous_employee = required_input("Enter the name of the previous employee: ")

                if validate_name(previous_employee):
                    break
                else:
                    print("Invalid name. Please enter a valid name containing at least one letter.")

            while True:
                previous_employee_id = required_input("Enter the employee ID of the previous employee: ")

                if validate_employee_id(previous_employee_id):
                    break
                else:
                    print("Invalid employee ID. Please enter a valid 7-digit employee ID.")

            return {
                "name":name,
                "department":department,
                "employee_id":employee_id,
                "date": submission_date,
                "role": "Taking over",
                "taking_over_from": previous_employee,
                "taking_over_from_id": previous_employee_id
            }
        else:
            print("Invalid option.")

# ===========================================================================
# Handover input  (uses: input handler)
# Lets the user type the handover, load a file with file:<name>, or drag in a .txt file.
# ===========================================================================    
def handover_input():
    while True:
        print("\nEnter the information for handover:")
        print("Enter text directly or type file:<filename> to load a .txt file.")

        handover_info = required_input("\nHandover: ")

        # Check if user wants to load a file
        if handover_info.lower().startswith("file:"):
            filename = handover_info[5:].strip()

            if filename == "":
                print("Please provide a filename.")
                continue

            handover_info = handover_from_file(filename)

            if handover_info is None:
                continue
        # Check if user dragged and dropped a file
        else:
            file_path = handover_info.strip()

            # Remove PowerShell's & prefix, if present
            if file_path.startswith("& "):
                file_path = file_path[2:].strip()

            # Remove surrounding quotation marks
            file_path = file_path.strip("'\"")

            path = Path(file_path)

            if path.suffix.lower() == ".txt" and path.is_file():
                handover_info = handover_from_file(path.name)

                if handover_info is None:
                    continue

            # Check sensitive information
            else:
                if validate_user_input(handover_info):
                    continue

        return handover_info

