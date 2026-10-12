
# ===========================================================================
# Setup - imports and paths
# ===========================================================================
import sys
from pprint import pformat
from pathlib import Path
# Ensure this file's directory (src/) is on sys.path so the sibling packages
# `modules` and `utils` import correctly no matter where the program is
# launched from.
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
     
# Team modules: logic manager, Gemini router (AI), output, data manager, input handler
import modules.logic_manager as logic_manager
from modules.gemini_router import send_to_llm
from modules import output
from modules import data_manager
from modules.input_handler import (
    get_user_details,
    required_input,
    handover_input,
    prompt_validated,
    validate_name, 
    validate_employee_id
)
from utils.logger import logger
from datetime import datetime

# ===========================================================================
# Settings
# ===========================================================================
DEBUG = False # Set to True for debugging mode


# ===========================================================================
# Prompt the user to correct missing or invalid task information
# ===========================================================================
def fill_missing_information(handover_data, errors):

    for error in errors:

        if error["type"] == "handover":
            print("No tasks were found. Please provide handover tasks.")
            return False

        task_type = error["type"]
        task_index = error["index"] - 1

        if task_type == "outstanding":
            task = handover_data["outstanding_tasks"][task_index]
        elif task_type == "bau":
            task = handover_data["bau_tasks"][task_index]
        else:
            continue

        print(f"\n--- {task_type.upper()} TASK {error['index']} ---")

        # Display "Not provided" if empty string
        print(f"Task Name: {task['task'] or 'Not provided'}") 
        print(f"Description: {task['description'] or 'Not provided'}")
        print(f"Owner(s): {', '.join(task['owners']) if task['owners'] else 'Not provided'}")

        # Only outstanding tasks has a deadline hence check task_type == "outstanding" before printing deadline
        if task_type == "outstanding":
            print(f"Deadline: {task['deadline'] or 'Not provided'}")

        for missing_field in error["errors"]:

            if missing_field == "task":
                task["task"] = required_input("\nMissing Task name. Please enter a task name: ")
            elif missing_field == "description":
                task["description"] = required_input("\nMissing task description. Please enter a description: ")
            elif missing_field == "missing_owner(s)":
                owner = required_input("\nMissing task owner(s). Please enter owner(s) separated by comma: ")
                task["owners"] = [o.strip() for o in owner.split(",") if o.strip()]
            elif missing_field in ("missing_deadline", "invalid_deadline"):
                # Inform user why the deadline needs to be entered again
                if missing_field == "missing_deadline":
                    print("\nDeadline is missing. Please provide a deadline.")
                elif missing_field == "invalid_deadline":
                    print("\nInvalid deadline. Please enter a valid date (today or later) in DD/MM/YYYY format.")

                task["deadline"] = prompt_validated(
                    "\nEnter deadline (DD/MM/YYYY): ",
                    logic_manager.validate_deadline,
                    "Invalid deadline. Please enter a valid date (today or later) in DD/MM/YYYY format."
                )
            else:
                logger.warning(
                    "Unhandled validation error '%s' on %s task %s",
                    missing_field,
                    task_type,
                    error.get("index")
                )
                print(f"\n[Notice] Unrecognized validation check '{missing_field}'. Please review this task.")
            
    return True

# ===========================================================================
# AI extraction  (uses: Gemini router)
# Sends the handover text to the AI and returns it as structured data (a dict).
# ===========================================================================
def get_handover_data():
    # Allow the user to resubmit handover information if AI processing fails
    while True:
        handover_info = handover_input()

        handover_data = send_to_llm(handover_info)

        # Check if send_to_llm returned an error envelope
        if handover_data.get("success") is False:
            err = handover_data.get("error_message", "")
            print(f"\n[AI Error]: {err}")

            # 1. Fatal Auth Error (API key missing or invalid)
            if "Authentication failed" in err:
                print("Action: Please check your GEMINI_API_KEY environment variable.")
                return None

            # 2. Rate Limit Hit (429)
            elif "Rate limit" in err:
                print("Action: AI quota exceeded. Please wait ~30 seconds before retrying.")

            # 3. Connection / Downtime (Network timeout, Server 5xx)
            elif "Network timeout" in err or "temporarily unavailable" in err:
                print("Action: Check your internet connection or server availability.")

            # 4. Parsing / Schema Failure (LLM produced unexpected JSON)
            elif "schema" in err or "Malformed JSON" in err:
                print("Action: The AI had trouble understanding the notes. Try rewording or providing more detail.")

            # Default / Unexpected
            else:
                print("Action: An unexpected error occurred.")

            # Ask user if they wish to retry
            retry = input("\nWould you like to try again? (y/n): ").strip().lower()
            if retry == "y":
                continue
            return None

        if DEBUG:
            print("\nDEBUG - AI Manager output:")
            print(pformat(handover_data, sort_dicts=False))

        return handover_data

# ===========================================================================
# Main program flow
# Handing over: Input -> AI -> Logic Manager -> Output -> Data Manager (Save)
# Taking over: Input -> Data Manager (Retrieve) -> Output -> Data Manager (Update)
# ===========================================================================
def main():

    # Step 1 - Input handler: get the user's details and role (handing over / taking over)
    user_details = get_user_details()

    # ----- HANDING OVER -----
    if user_details["role"] == "Handing over":
        # Step 2 - Input handler + Gemini router: get the handover text and pass to Gemini to put structure into Data
        handover_data = get_handover_data()
        if not handover_data:
            print("\nHandover process cancelled.")
            return 

        # Step 3 - Logic manager: validate, and keep asking for missing info until complete
        while True:

            # Validate stored handover data
            result = logic_manager.process_handover(handover_data)

            if result["status"] == "complete":
                # Step 4 - Output: show the status and generate the summary .txt
                filename = output.show_output(result, user_details)
                print("\nHandover is complete.")
                # Step 5 - Data manager: save the completed handover to data/handovers.json
                saved = data_manager.save_handover(user_details, result, filename)
                if not saved:
                    print("\n[Warning] Could not save handover to database. Please check file permissions.")

                if DEBUG:
                    print(f"\n{pformat(result, sort_dicts=False)}")

                break

            print("\nHandover is incomplete.")
            
            if DEBUG: 
                print(f"\n{pformat(result, sort_dicts=False)}")

            # Ask user to fill in missing information
            if not fill_missing_information(handover_data, result["errors"]):
                handover_data = get_handover_data()
                if not handover_data:
                    print("\nHandover process cancelled.")
                    return 

    # ----- TAKING OVER -----
    elif user_details["role"] == "Taking over":
        # Step 2 - Data manager: find the handover saved by the previous employee,
        # using the 7-digit ID the user typed for the previous employee
        previous_id = user_details["taking_over_from_id"]
        records = data_manager.get_records_by_employee_id(previous_id)
        
        # An empty list means nothing was found
        if not records:
            print(f"\nNo handover found for employee ID {previous_id}.")
            # return user_details
        
        handover = records[0]  # newest handover comes first
        print(f"\nFound handover from {handover['name']} ({handover['department']}), saved on {handover['saved_date']}.")
        
        # Step 3 - Ask for employee details to update viewing history
        name = prompt_validated(
            "\nEnter your name: ",
            validate_name,
            "Invalid name. Please enter a valid name containing at least one letter."
        )
        while True:
            employee_id = prompt_validated(
            "Enter your employee ID: ",
            validate_employee_id,
            "Invalid employee ID. Please enter a valid 7-digit employee ID."
        )
            if employee_id == str(previous_id):
                print("You cannot use the same employee ID as the previous employee. Please enter a different ID.")
                continue
            break
        
        # Step 4 - Output: Opens the fetched handover
        output.show_output(
            {**handover, "status": "complete"},
            handover,
            save_file=False
        )

        # Display previous viewers before recording the current viewer
        previous_viewers = handover.get("viewed_by", [])

        print("\n\n" + "=" * output.WIDTH)
        print("VIEWING HISTORY")
        print("=" * output.WIDTH)

        if previous_viewers:
            print(output.format_viewing_history(previous_viewers))
        else:
            print("No previous views recorded.")

        # Record the viewer in handovers.json
        updated = data_manager.add_viewer(
            handover["id"],
            name,
            employee_id
        )

        if updated:
            file_updated = output.append_viewing_history(
                handover.get("filename"),
                name,
                employee_id
            )

            if file_updated:
                print("\nViewing history updated successfully.")
            else:
                print("\n[Warning] Viewing history saved to JSON, but the .txt file could not be updated.")
        else:
            print("\n[Error] Could not update viewing history.")
        
        # return user_details
    
        
    # ----- DELETE HANDOVER -----
    elif user_details["role"] == "Delete":
        employee_id = user_details["employee_id"]

        # Retrieve saved handovers belonging to the employee
        records = data_manager.get_records_by_employee_id(employee_id)

        if not records:
            print(f"\nNo saved handovers found for employee ID {employee_id}.")
            return user_details

        # Display the available handovers
        print(f"\nSaved handovers for {user_details['name']} ({employee_id}):")

        for index, record in enumerate(records, start=1):
            filename = record.get("filename") or "Filename unavailable"
            print(f"{index}. {filename}")

        print("0. Cancel")

        # Ask the user to select a handover
        while True:
            choice = input("\nSelect a handover to delete: ").strip()

            if choice == "0":
                print("\nDeletion cancelled.")
                return user_details

            if choice.isdigit() and 1 <= int(choice) <= len(records):
                selected_record = records[int(choice) - 1]
                break

            print("Invalid selection. Please select a number from the list.")

        # Confirm before deleting
        filename = selected_record.get("filename")

        print(f"\nSelected file: {filename or 'Filename unavailable'}")

        while True:
            confirm = input("Are you sure you want to delete this handover? (y/n): ").strip().lower()

            if confirm == "y":
                break

            if confirm == "n":
                print("\nDeletion cancelled.")
                return user_details

            print("Invalid input. Please enter y or n.")

        # Delete the selected handover record from JSON
        record_deleted = data_manager.delete_record(selected_record["id"])

        if record_deleted:
            # Delete the corresponding .txt summary file
            if filename:
                file_deleted = data_manager.delete_summary_files(filename)

                if file_deleted:
                    print("\nHandover deleted successfully.")
                else:
                    print("\nHandover record deleted, but the summary .txt file could not be deleted.")
            else:
                print("\nHandover record deleted. No summary filename was linked.")

        else:
            print("\n[Error] Could not delete the handover record.")

# ===========================================================================
# Program entry point
# ===========================================================================
if __name__ == "__main__":
    while True:
        result = main()
        choice = input("\nWould you like to perform another action? (y/n): ").strip().lower()
        if choice == "n":
            print("Thank you for using the Handover Management System.")
            break
            sys.exit
        elif choice == "y":
            print("\nRestarting the program...\n")
        else:
            print("Invalid input. Restarting the program.")