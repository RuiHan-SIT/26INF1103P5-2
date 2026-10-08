import sys
from pathlib import Path

# Ensure this file's directory (src/) is on sys.path so the sibling packages
# `modules` and `utils` import correctly no matter where the program is
# launched from.
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from modules.input_handler import (
    get_user_details,
    handover_from_file,
    required_input,
    validate_user_input,
)


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
            if not validate_user_input(handover_info):
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

if __name__ == "__main__":
    main()
