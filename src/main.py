import sys
from pathlib import Path
import src.modules.logic_manager as logic_manager
import src.modules.data_manager as data_manager

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

from modules.nvidia_router import send_to_llm

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

        try:
            llm_result = send_to_llm(handover_info)
        except ValueError as e:
            # Defensive: send_to_llm() currently raises ValueError on a
            # Pydantic validation failure instead of returning an error dict
            # like its other failure paths. Catch it here so a bad LLM
            # response can't crash the whole pipeline.
            print(f"Couldn't process handover: {e}")
            return None

        # send_to_llm returns a dict with success=False on failure,
        # or a HandoverReport (Pydantic model) on success
        if isinstance(llm_result, dict) and llm_result.get("success") is False:
            print(f"Couldn't process handover: {llm_result['error_message']}")
            return None

        llm_data = llm_result.model_dump()                # Pydantic model -> plain dict
        result = logic_manager.process_handover(llm_data)  # Logic Manager validates + sorts

        if result["status"] == "incomplete":
            print("Handover is incomplete:", result["errors"])
            return None

        final_record = {**user_details, **result}
        data_manager.add_record(final_record)              # Data Manager: Create
        print("Handover saved.")
        return final_record

    elif user_details["role"] == "Taking over":
        print("Taking over information successfully validated.")

        records = data_manager.load_records()              # Data Manager: Read
        return user_details, records

if __name__ == "__main__":
    result = main()



# error handling done by nvidia file 

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