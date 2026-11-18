from utils.logger import logger
from pathlib import Path
import scrubadub
from datetime import datetime
from modules import data_manager
import re
# Build the Scrubber once and reuse it across calls (construction is not free).
_scrubber = scrubadub.Scrubber()
_scrubber.remove_detector('phone')
from utils.config import HANDOVERS_DIR
handover_dir = HANDOVERS_DIR


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
    "NRIC/FIN": r"\b[STFGM]\d{7}[A-Z]\b",                                                                                                
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
            "\n"
            "Sensitive information detected: "
            f"{', '.join(sorted(detected_types))}. "
            "Please remove any sensitive information before proceeding."
        )
        return True

    return False

# ===========================================================================
# Helper Functions 
# Validate user input
# ===========================================================================

def has_alphabetic_char(text: str) -> bool:                                                                                                                                          
    """Checks if a string is non-empty and contains at least one letter."""                                                                                                          
    return bool(text.strip()) and any(char.isalpha() for char in text) 

def validate_name(name: str) -> bool:                                                                                                                                    
    return has_alphabetic_char(name)
    
def validate_department(department: str) -> bool:                                                                                                                                    
    return has_alphabetic_char(department)                                                                                                                                           
                                                                                                                                                                                         
def validate_employee_id(employee_id: str) -> bool:                                                                                                                                  
    return len(employee_id) == 7 and employee_id.isdigit()

def required_input(prompt, allow_back=False):
    while True:
        value = input(prompt).strip()

        if allow_back and value == "0":
            return None

        if value == "":
            print("This field is required. Please enter a value.")
        else:
            return value

def prompt_validated(prompt: str, validator, error_message: str, allow_back=False):
    """Prompt until valid input is entered, or return None if user goes back."""
    while True:
        value = input(prompt).strip()

        if allow_back and value == "0":
            return None

        if not value:
            print("This field is required. Please enter a value.")
            continue

        if validator(value):
            return value

        print(error_message)

def process_file_content(file_path):
    """Read, validate file size/encoding, and check for sensitive data."""
    handover_info = read_txt_file(file_path)
    if handover_info is None:
        return None

    if validate_user_input(handover_info):
        return None

    return handover_info

def handover_from_file(filename):
    # Read and validate a handover .txt file by name (looked up in handover_dir).
    # returns the file text if valid and clean, otherwise None so the caller can
    # decide how to proceed (e.g. re-prompt).

    input_file = (handover_dir / filename).resolve()
    if not input_file.is_relative_to(handover_dir.resolve()):
        print("Invalid file path. Please provide a valid filename within the handover directory.")
        return None

    return process_file_content(input_file)

def get_user_details():
    # Display the main menu before requesting user details
    print("\n" + "=" * 45)
    print("             AI HANDOVER ASSISTANT")
    print("=" * 45)
    print("\nWhat would you like to do?")
    print("1. Create a new handover")
    print("2. View a handover")
    print("3. Delete a handover")
    print("0. Exit")

    while True:
        role = required_input("\nSelect an option: ")
        
        if role == "0":
            return None

        if role == "1":
            while True:
                employee_id = prompt_validated(
                    "\nEnter your employee ID (0 to go back): ",
                    validate_employee_id,
                    "Invalid employee ID. Please enter a valid 7-digit employee ID.",
                    allow_back=True
                )

                if employee_id is None:
                    print("\nReturning to main menu...")
                    return "BACK"

                # Retrieve employee details from the company database
                employee = data_manager.get_employee(employee_id)

                if employee is None:
                    print("\nEmployee ID not found. Please check your employee ID and try again.")
                    continue

                # Display employee details for confirmation
                print(f"\nEmployee found: {employee['name']}")
                print(f"Department: {employee['department']}")

                confirm = input("\nIs this you? (y/n or 0 to go back): ").strip().lower()

                if confirm == "0":
                    print("\nReturning to main menu...")
                    return "BACK"

                if confirm == "y":
                    return {
                        "name": employee["name"],
                        "department": employee["department"],
                        "employee_id": employee_id,
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "role": "Handing over"
                    }

                if confirm == "n":
                    print("\nPlease check your employee ID and try again.")
                else:
                    print("\nInvalid input. Please enter y/n or 0.")

        elif role == "2":
            # Retrieve the handover using the previous employee's ID
            previous_employee_id = prompt_validated(
                "\nEnter the employee ID of the person handing over (0 to go back): ",
                validate_employee_id,
                "Invalid employee ID. Please enter a valid 7-digit employee ID.",
                allow_back=True
            )

            if previous_employee_id is None:
                print("\nReturning to main menu...")
                return "BACK"
            
            while True:
                #get the receiving employee's ID to ensure that the handover is being taken over by the correct person
                employee_id = prompt_validated(
                    "\nEnter your employee ID (0 to go back): ",
                    validate_employee_id,
                    "Invalid employee ID. Please enter a valid 7-digit employee ID.",
                    allow_back=True
                )

                if employee_id is None:
                    print("\nReturning to main menu...")
                    return "BACK"

                employee = data_manager.get_employee(employee_id)
                if employee is None:
                    print("\nEmployee ID not found. Please check your employee ID and try again.")
                    continue

                # Display employee details for confirmation
                print(f"\nEmployee found: {employee['name']}")
                print(f"Department: {employee['department']}")

                while True:
                    confirm = input("\nIs this you? (y/n or 0 to go back): ").strip().lower()

                    if confirm == "0":
                        print("\nReturning to main menu...")
                        return "BACK"

                    if confirm == "y":
                        return {
                            "name": employee["name"],
                            "department": employee["department"],
                            "employee_id": employee_id,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "role": "Taking over",
                            "taking_over_from_id": previous_employee_id
            }
    
                    if confirm == "n":
                        print("\nPlease check your employee ID and try again.")
                        break

                    print("\nInvalid input. Please enter y/n or 0.")

        elif role == "3":
            while True:
                employee_id = prompt_validated(
                    "\nEnter your employee ID (0 to go back): ",
                    validate_employee_id,
                    "Invalid employee ID. Please enter a valid 7-digit employee ID.",
                    allow_back=True
                )

                if employee_id is None:
                    print("\nReturning to main menu...")
                    return "BACK"

                # Retrieve employee details from the company database
                employee = data_manager.get_employee(employee_id)

                if employee is None:
                    print("\nEmployee ID not found. Please check your employee ID and try again.")
                    continue

                # Display employee details for confirmation
                print(f"\nEmployee found: {employee['name']}")
                print(f"Department: {employee['department']}")

                while True:
                    confirm = input("\nIs this you? (y/n or 0 to go back): ").strip().lower()

                    if confirm == "0":
                        print("\nReturning to main menu...")
                        return "BACK"

                    if confirm == "y":
                        return {
                            "role": "Delete",
                            "employee_id": employee_id,
                            "name": employee["name"],
                            "department": employee["department"]
                        }

                    if confirm == "n":
                        print("\nPlease check your employee ID and try again.")
                        break

                    print("\nInvalid input. Please enter y/n or 0.")

# ===========================================================================
# Handover input  (uses: input handler)
# Lets the user type the handover, load a file with file:<name>, or drag in a .txt file.
# ===========================================================================    
def handover_input():
    while True:
        print("\nEnter the information for handover:")
        print("Enter text directly or type file:<filename> to load a .txt file.")
        print("Enter 0 to return to the main menu.")

        handover_info = required_input("\nHandover: ")

        if handover_info == "0":
            print("\nReturning to main menu...")
            return None

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
                handover_info = process_file_content(path.resolve())

                if handover_info is None:
                    continue

            # Check sensitive information
            else:
                if validate_user_input(handover_info):
                    continue

        return handover_info

