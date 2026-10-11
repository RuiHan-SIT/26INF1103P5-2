
import json
from pathlib import Path

import main as app_main
from modules.input_handler import handover_dir

BASE_DIR = Path(__file__).resolve().parent.parent
RESPONSES_DIR = BASE_DIR / "data" / "offline_responses"


def send_to_llm_offline(handover_text):
    """
    Replace Gemini with a saved response matching the selected text file.
    No API request is made.
    """

    # Find the original .txt file containing the submitted handover text.
    matched_file = None

    for txt_file in handover_dir.glob("*.txt"):
        try:
            file_text = txt_file.read_text(encoding="utf-8")
            if file_text.strip() == handover_text.strip():
                matched_file = txt_file
                break
        except (OSError, UnicodeDecodeError):
            continue

    
    if matched_file is None:
        return {
            "success": False,
            "data": None,
            "error_message": (
                "No saved offline response matches this handover. "
                "Please use a prepared .txt handover with a matching "
                "saved JSON response, or prepare a response first."
            ),
        }

    # Find the cached Gemini response with the matching filename.
    response_path = RESPONSES_DIR / f"{matched_file.stem}.json"

    if not response_path.is_file():
        return {
        "success": False,
            "data": None,
            "error_message": (
                f"No saved response exists for {matched_file.name}. "
                "Prepare its response before the presentation."
            ),
        }

    try:
        with response_path.open("r", encoding="utf-8") as file:
            handover_data = json.load(file)

        if not isinstance(handover_data, dict):
            raise ValueError("The saved response must be a JSON object.")

        print("\n[OFFLINE MODE] Using a saved Gemini response.")
        print("[OFFLINE MODE] No API request was made.")

        return handover_data

    except (OSError, json.JSONDecodeError, ValueError) as error:
        return {
            "success": False,
            "data": None,
            "error_message": f"Could not load saved response: {error}",
        }


def main():
    print("\n" + "=" * 60)
    print("HANDOVER AUDITOR - OFFLINE DEMONSTRATION")
    print("Gemini API: DISABLED")
    print("=" * 60)

    # Replace only the AI function.
    # All other CLI steps continue to use the real main.py workflow.
    app_main.send_to_llm = send_to_llm_offline

    # Run the original CLI, including user details and role selection.
    app_main.main()


if __name__ == "__main__":
    main()