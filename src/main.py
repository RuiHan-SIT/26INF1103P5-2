
import sys
from pprint import pformat
from pathlib import Path

# Ensure this file's directory (src/) is on sys.path so the sibling packages
# `modules` and `utils` import correctly no matter where the program is
# launched from.
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import modules.logic_manager as logic_manager
from modules.gemini_router import send_to_llm
from modules.input_handler import (
    get_user_details,
    handover_from_file,
    required_input,
    validate_user_input,
    handover_input
)


def main():

    user_details = get_user_details()

    handover_input()


    if user_details["role"] == "Handing over":
        handover_info = handover_input()
        print("Input is successfully validated.")

        # Pass handover output to AI Manager
        llm_output = send_to_llm(handover_info)

        # Convert AI output into dictionary
        handover_data = llm_output.model_dump()

        # Pass dictionary to Logic Manager
        result = logic_manager.process_handover(handover_data)

        # Check handover status
        if result["status"] == "incomplete":
            print("\nHandover is incomplete.")
            print(pformat(result, sort_dicts=False))

            for error in result["errors"]:
                print(error)

        else:
            print("\nHandover is complete.")
            print(pformat(result, sort_dicts=False))

    elif user_details["role"] == "Taking over":
        #able to call data manager to return selected id file 
        print("Taking over information successfully validated.")
        return user_details
    
if __name__ == "__main__":
    result = main()



# error handling done by gemini_router file

# result = analyze_handover_safe(file_text)

# if not result["success"]:
#     print(f"\n[!] Failed to process handover: {result['error_message']}\n")
# else:
#     handover = result["data"]
#     print(f"\n[+] Successfully Analyzed: {handover.summary}")
#     print("Action Items:")
#     for task in handover.action_items:
#         print(f" - {task}")



"""
- idempotent handling (  Idempotent = doing something more than once gives the same result as doing it once.)
- ai able to call data.json and verify but asking for user input. 

Business Logic:
IMPORTANT: Main.py should check for exisitng data than fill in the blanks.
1) input 
2) validate user input 
3) pass to llm to organise the data with my system prompt and user prompt ( stream disable not needed for now )
4) llm output is pass to logic manager 
5) logic maanger passes then it will call data manager to save data
6) data manager saves data tagged to the hoto 
"""