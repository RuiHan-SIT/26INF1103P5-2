
import json
from pathlib import Path

from modules.input_handler import handover_from_file
from modules.gemini_router import send_to_llm


BASE_DIR = Path(__file__).resolve().parent.parent
RESPONSES_DIR = BASE_DIR / "data" / "offline_responses"


def main():
    print("\n=== PREPARE OFFLINE HANDOVER RESPONSE ===")
    print("This preparation step requires Gemini to be available.")

    filename = input(
        "\nEnter handover filename (e.g. handover.txt): "
    ).strip()

    if not filename.lower().endswith(".txt"):
        print("Please enter a .txt filename.")
        return

    # Read the real text file using your existing input validation.
    handover_text = handover_from_file(filename)

    if handover_text is None:
        print("Unable to load the handover file.")
        return

    print("\nSending the handover text to Gemini...")

    # Call Gemini once to obtain the real structured response.
    handover_data = send_to_llm(handover_text)

    # Your Gemini router returns this error envelope on failure.
    if (
        not isinstance(handover_data, dict)
        or handover_data.get("success") is False
    ):
        error = (
            handover_data.get("error_message", "Unknown AI error")
            if isinstance(handover_data, dict)
            else "Gemini returned an unexpected response."
        )
        print(f"\nCould not prepare offline response: {error}")
        return

    # Save the actual validated Gemini response.
    response_path = (
        RESPONSES_DIR / f"{Path(filename).stem}.json"
    )

    try:
        RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

        with response_path.open("w", encoding="utf-8") as file:
            json.dump(
                handover_data,
                file,
                indent=4,
                ensure_ascii=False
            )

        print("\nGemini response saved successfully.")
        print(f"Saved to: {response_path}")
        print("You can now replay this response without an API call.")

    except OSError as error:
        print(f"\nCould not save the response: {error}")


if __name__ == "__main__":
    main()