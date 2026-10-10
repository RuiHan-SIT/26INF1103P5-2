
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
    handover_from_file,
    required_input,
    validate_user_input,
    handover_input
)

# ===========================================================================
# Settings
# ===========================================================================
DEBUG = False # Change to False when out of debugging mode


# ===========================================================================
# Fill in missing information  (uses: logic manager)
# Asks the user for any task name, description, owner or deadline the logic manager flagged.
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
                task["task"] = input("\nEnter task name: ").strip()
            elif missing_field == "description":
                task["description"] = input("\nEnter description: ").strip()
            elif missing_field == "missing_owner(s)":
                owner = input("\nEnter owner: ").strip()
                task["owners"] = [owner] if owner else []
            elif missing_field in ("missing_deadline", "invalid_deadline"):

                # Inform user why the deadline needs to be entered again
                if missing_field == "missing_deadline":
                    print("\nDeadline is missing. Please provide a deadline.")
                elif missing_field == "invalid_deadline":
                    print("\nInvalid deadline. Please enter a valid date (today or later) in DD/MM/YYYY format.")

                while True:
                    deadline = input("\nEnter deadline (DD/MM/YYYY): ").strip()

                    if logic_manager.validate_deadline(deadline):
                        task["deadline"] = deadline
                        break

                    print("Invalid deadline. Please enter a valid date (today or later) in DD/MM/YYYY format.")
            else:
                raise ValueError(f"Unhandled validation error: {missing_field}")
            
    return True

# ===========================================================================
# AI extraction  (uses: Gemini router)
# Sends the handover text to the AI and returns it as structured data (a dict).
# ===========================================================================
def get_handover_data():
    # Only calls handover info when needed..
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
# Handing over: input -> AI -> logic manager -> output -> data manager (save)
# Taking over : input -> data manager (find) -> output
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
            return user_details

        # Step 3 - Logic manager: validate, and keep asking for missing info until complete
        while True:

            # Validate stored handover data
            result = logic_manager.process_handover(handover_data)

            if result["status"] == "complete":
                # Step 4 - Output: show the status and generate the summary .txt
                output.show_output(result)
                print("\nHandover is complete.")
                # Step 5 - Data manager: save the completed handover to data/handovers.json
                data_manager.save_handover(user_details, result)

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
                    return user_details

    # ----- TAKING OVER -----
    elif user_details["role"] == "Taking over":
        # Step 2 - Data manager: find the handover saved by the previous employee,
        # using the 7-digit ID the user typed for the previous employee
        previous_id = user_details["taking_over_from_id"]
        records = data_manager.get_records_by_employee_id(previous_id)
        
        # An empty list means nothing was found
        if not records:
            print(f"\nNo handover found for employee ID {previous_id}.")
            return user_details
        
        handover = records[0]  # newest handover comes first
        print(f"\nFound handover from {handover['name']} ({handover['department']}), saved on {handover['saved_date']}.")
        
        # Step 3 - Output: generate a summary .txt file from the fetched handover
        output.show_output({**handover, "status": "complete"})
        return user_details
    
# ===========================================================================
# Program entry point
# ===========================================================================
if __name__ == "__main__":
    result = main()





"""
Business Logic:
IMPORTANT: Main.py should check for exisitng data than fill in the blanks.
1) input 
2) validate user input 
3) pass to llm to organise the data with my system prompt and user prompt ( stream disable not needed for now )
4) llm output is pass to logic manager 
5) logic maanger passes then it will call data manager to save data
6) data manager saves data tagged to the hoto 
"""