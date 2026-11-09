from .constants import (
    COMPLETE_STATUSES,
    INCOMPLETE_STATUSES,
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
    VIEWING_HEADING,
)
from .summary_file_store import SummaryFileStore
from .summary_formatter import SummaryFormatter


class OutputManager:
    """Prepares handover output for the GUI."""

    def __init__(self):
        # Each helper class handles a separate job
        self._formatter = SummaryFormatter()
        self._store = SummaryFileStore()

    def show_output(self, result, user_details=None, save_file=False):
        """Return information that a Django view can pass to a template."""
        status = str(result.get("status", "Unknown")).strip()
        normalized_status = status.lower()

        is_complete = normalized_status in COMPLETE_STATUSES
        is_incomplete = normalized_status in INCOMPLETE_STATUSES

        output = {
            "status": self._status_label(normalized_status, status),
            "is_complete": is_complete,
            "missing": [],
            "data": result,
            "summary": "",
            "filename": None,
            "error": None,
        }

        if is_incomplete:
            output["missing"] = self._missing_lines(result)

        # Don't format or save a summary for an incomplete handover
        if not is_complete:
            return output

        output["summary"] = self._formatter.format(result, user_details)

        # Saving a separate text file is optional; the GUI can display the
        # summary without writing an extra file
        if save_file:
            try:
                output["filename"] = self._store.save(
                    output["summary"],
                    user_details or {},
                )
            except OSError as error:
                output["error"] = f"Could not save summary file: {error}"

        return output

    def record_view(self, filename, name, employee_id):
        """Add a viewing record to an optional saved text summary."""
        if not filename:
            return False, "No filename linked to this handover."

        try:
            if not self._store.exists(filename):
                return False, "Handover summary file not found."

            current_text = self._store.read(filename)

            # Add the heading if this is the first viewing record
            is_first_view = VIEWING_HEADING not in current_text
            entry = self._formatter.format_viewing_entry(
                name,
                employee_id,
                is_first_view,
            )
            self._store.append(filename, entry)

        except (OSError, ValueError) as error:
            return False, f"Could not update viewing history: {error}"

        return True, "Viewing history updated."

    def read_summary(self, filename):
        """Read a saved text summary, or return None if it doesn't exist."""
        if not filename:
            return None

        try:
            if self._store.exists(filename):
                return self._store.read(filename)
        except (OSError, ValueError):
            return None

        return None

    def _status_label(self, normalized_status, original_status):
        if normalized_status in COMPLETE_STATUSES:
            return STATUS_COMPLETE

        if normalized_status in INCOMPLETE_STATUSES:
            return STATUS_INCOMPLETE

        return original_status

    def _missing_lines(self, result):
        # The logic manager may call these entries "errors" instead
        missing_info = result.get("missing_info") or result.get("errors") or []
        lines = []

        for item in missing_info:
            if isinstance(item, dict):
                label = item.get("task", item.get("type", "Handover"))
                errors = item.get("errors", [])

                if isinstance(errors, list):
                    details = ", ".join(str(error) for error in errors)
                else:
                    details = str(errors)

                lines.append(f"{label}: {details or item}")
            else:
                lines.append(str(item))

        return lines