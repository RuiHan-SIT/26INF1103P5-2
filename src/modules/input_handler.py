from utils.logger import logger
from pathlib import Path
import scrubadub
from datetime import datetime

# Build the Scrubber once and reuse it across calls (construction is not free).
_scrubber = scrubadub.Scrubber()

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


def validate_user_input(text: str):  
    # scrubadub detects structured PII: emails, phone numbers, credit cards, etc.
    detected_types = {filth.type for filth in _scrubber.iter_filth(text)}

    # keyword check for domain-sensitive words scrubadub does not model as PII
    sensitive_keywords = [
        "password", "credit card", "bank account", "nric", "passport",
        "driver's license", "confidential", "secret", "private", "restricted",
    ]
    text_lower = text.lower()
    for keyword in sensitive_keywords:
        if keyword in text_lower:
            detected_types.add(keyword)

    if detected_types:
        print(
            "Sensitive information detected: "
            f"{', '.join(sorted(detected_types))}. "
            "Please remove any sensitive information before proceeding."
        )
        return True

    return False

def handover_from_file(filename):
    #Read and validate a handover .txt file by name (looked up in handover_dir).
    #returns the file text if valid and clean, otherwise None so the caller can
    #decide how to proceed (e.g. re-prompt).

    input_file = handover_dir / filename

    handover_info = read_txt_file(input_file)
    if handover_info is None:
        return None

    if validate_user_input(handover_info):
        return None

    return handover_info

#function to get user details
def get_user_details(): #function to get user details
    name = required_input("Enter your name: ") #employee name
    department = required_input("Enter your department: ") #employee department

    submission_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S") #get current date and time
    print("\n Are you:")
    print("1. Handing over work") #letting employee choose whether to handover or takeover
    print("2. Taking over work") 

    while True:
        role = required_input("Select an option: ") 

        if role == "1":

            return {                        #stores information in a dictionary
                "name": name,
                "department": department,
                "date":submission_date,
                "role": "Handing over"
            }
        elif role == "2":

            previous_employee = required_input("Enter the name of the previous employee: ") #enters the details of previous empployee to extract the handover document
            previous_department = required_input("Enter their department:")

            return {
                "name":name,
                "department":department,
                "date": submission_date,
                "role": "Taking over",
                "taking_over_from": previous_employee,
                "taking_over_department": previous_department
            }
        else:
            print("Invalid option.")

def required_input(prompt): #this is to ensure manually added information for required fields
    while True:
        value = input(prompt).strip()

        if value == "":
            
            print("This field is required. Please enter a value.")
        else:
            return value

def handover_input():
    while True:
        print("\nEnter the information for handover:")
        print("Enter text directly or type file:<filename> to load a .txt file.") #a singular input for user to choose between texxt or file upload

        handover_info = required_input("\nHandover: ")

        #check if user wants to load a file
        if handover_info.lower().startswith("file:"):
            filename = handover_info[5:].strip()

            if filename == "":
                print("Please provide a filename.")
                continue

            handover_info = handover_from_file(filename)

            if handover_info is None:
                continue

        #check sensitive information
        else:
            if validate_user_input(handover_info):
                continue


        return handover_info

def main():
    user_details = get_user_details()

    if user_details["role"] == "Handing over":
        handover_info = handover_input()

        print("Input is successfully validated.")

        return user_details, handover_info

    elif user_details["role"] == "Taking over":
        print("Taking over information successfully validated.")

        return user_details