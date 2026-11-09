# output_manager.py
from .constants import (
    COMPLETE_STATUSES,
    INCOMPLETE_STATUSES,
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
    VIEWING_HEADING,
    WIDTH,
)
from .summary_file_store import SummaryFileStore
from .summary_formatter import SummaryFormatter


class OutputManager:
    """The class main.py uses. It shows the status, prints or saves the summary, and records who viewed a handover.

    It does not build the text or handle files itself. It asks SummaryFormatter and SummaryFileStore to do those jobs.
    """

    def __init__(self):
        
        self._formatter = SummaryFormatter()
        self._store = SummaryFileStore()

    def show_output(self, result, user_details, save_file=True):
        """Main method called with the logic manager's result.

        save_file=True : show the status, then save the summary if complete.
        save_file=False: only print the summary in the terminal if complete.
        Returns the saved file name, or None.
        """
        if save_file:
            self.show_status(result)

        # Only a complete handover gets a summary
        if result.get("status") not in COMPLETE_STATUSES:
            return None

        summary_text = self._formatter.format(result, user_details)

        if save_file:
            return self._save_summary(summary_text, user_details)

        print("\n" + summary_text)
        return None

    def show_status(self, result):
        """Print the handover status, and what is missing if it is incomplete."""
        status = result.get("status", "Unknown")

        # Choose the text to display for this status
        if status in COMPLETE_STATUSES:
            label = STATUS_COMPLETE
        elif status in INCOMPLETE_STATUSES:
            label = STATUS_INCOMPLETE
        else:
            label = str(status)

        print("\n" + "=" * WIDTH)
        print("STATUS: " + label.upper())
        print("=" * WIDTH)

        if status in INCOMPLETE_STATUSES:
            # Some versions of the result use "errors" instead of "missing_info"
            missing_info = result.get("missing_info", result.get("errors", []))
            self._print_missing_info(missing_info)
            print("\nPlease resolve the items above, then run the handover again.")

    def record_view(self, filename, name, employee_id):
        """Record that someone viewed a saved handover. Returns True if it worked."""
        if not filename:
            print("\n[Warning] No filename linked to this handover.")
            return False

        if not self._store.exists(filename):
            print("\n[Warning] Handover summary file not found.")
            return False

        try:
            # Add the heading only if this is the first viewer
            current_text = self._store.read(filename)
            is_first_view = VIEWING_HEADING not in current_text

            entry = self._formatter.format_viewing_entry(name, employee_id, is_first_view)
            self._store.append(filename, entry)
            return True
        except OSError as error:  # e.g. file is locked or disk problem
            print(f"\n[Error] Could not update viewing history: {error}")
            return False

    # ---- private helper methods ----

    def _save_summary(self, summary_text, user_details):
        """Save the summary file. Returns the file name, or None if it failed."""
        try:
            filename = self._store.save(summary_text, user_details)
        except OSError as error:  # e.g. no permission to write
            print(f"\n[Error] Could not save summary file: {error}")
            return None

        print(f"\nHandover file saved to: {filename}")
        return filename

    def _print_missing_info(self, missing_info):
        """List the items that need clarification."""
        if not missing_info:
            return

        print("\nClarification needed:")
        for item in missing_info:
            if isinstance(item, dict):
                # Item looks like {"task": "Deploy", "errors": ["No owner"]}
                label = item.get("task", item.get("type", "Handover"))
                details = ", ".join(item.get("errors", []))
                print(f"  - {label}: {details or item}")
            else:
                # Item is just a plain text message
                print(f"  - {item}")