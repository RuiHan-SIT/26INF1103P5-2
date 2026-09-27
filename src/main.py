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
    get_handover_info,
    handover_from_file,
)


def collect_handover_info():
    """Ask how the user wants to provide handover info, then collect it."""
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
                    more = input("\nDo you want to add more tasks? (yes/no): ").lower()
                    if more in ("yes", "no"):
                        break
                    print("Invalid input. Please enter yes or no")

                if more == "no":
                    break

            return tasks

        elif choice == "2":
            filename = input("Enter the .txt filename: ")
            handover_info = handover_from_file(filename)
            if handover_info is None:
                # invalid / not found / contained sensitive info: re-prompt
                continue
            return handover_info

        else:
            print("Invalid option. Please select 1 or 2.")


def main():
    user_details = get_user_details()
    if user_details is None:
        return None

    name, department, handover_role = user_details

    if handover_role == "Handing over":
        handover_info = collect_handover_info()
        if handover_info is None:
            return None

        print("Input is successfully validated.")
        return name, department, handover_role, handover_info

    elif handover_role == "Taking over":
        print("No handover input required.")
        return name, department, handover_role

    return None


if __name__ == "__main__":
    main()
