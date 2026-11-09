from datetime import datetime
from pathlib import Path

SUMMARIES_DIR = Path(__file__).resolve().parents[4] / "data" / "summaries"


class SummaryFileStore:
    """Handles the summary .txt files: save, check, read and add to them."""

    def __init__(self):
        # The folder where all summaries are kept (set in utils/config.py)
        self._folder = SUMMARIES_DIR

    def save(self, text, user_details):
        """Save a new summary file and return its file name."""
        filename = self._make_filename(user_details)
        self._folder.mkdir(parents=True, exist_ok=True)  # create the folder if needed
        (self._folder / filename).write_text(text, encoding="utf-8")
        return filename

    def exists(self, filename):
        """True if a summary file with this name exists."""
        return (self._folder / filename).is_file()

    def read(self, filename):
        """Return the full text of a saved summary."""
        return (self._folder / filename).read_text(encoding="utf-8")

    def append(self, filename, text):
        """Add text to the end of an existing summary (mode 'a' = append)."""
        with open(self._folder / filename, "a", encoding="utf-8") as file:
            file.write(text)

    def _make_filename(self, user_details):
        """Example: 2026-11-08_Goh_Rui_Han_E001_10-30-15.txt"""
        now = datetime.now()

        # Replace anything that is not safe in a file name (e.g. / or :) with _
        safe_name = ""
        for char in user_details["name"]:
            if char.isalnum() or char in "-_":
                safe_name += char
            else:
                safe_name += "_"

        employee_id = user_details["employee_id"]
        # Date + name + ID + time makes every file name unique
        return f"{now:%Y-%m-%d}_{safe_name}_{employee_id}_{now:%H-%M-%S}.txt"