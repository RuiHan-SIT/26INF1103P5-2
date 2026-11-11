# The IO Manager of the web app. Views call this class to get the handover
# status and summary in a form the page can show. It never prints: it RETURNS
# data, and the Django view / template decides how to display it.

import logging

from .constants import (
    COMPLETE_STATUSES,
    LABEL_COMPLETED,
    LABEL_NEEDS_CLARIFICATION,
    VIEWING_HEADING,
)
from .summary_file_store import SummaryFileStore
from .summary_formatter import SummaryFormatter

logger = logging.getLogger(__name__)


class OutputManager:
    """Prepares what the website shows for a handover and saves its summary."""

    def __init__(self, store=None):
        # OutputManager is made of these two helpers (composition)
        # "store" is only passed in by the tests (to use a fake instead of real files)
        self._formatter = SummaryFormatter()
        self._store = store or SummaryFileStore()

    # ---- public (called by the views / Controller) -----------------------
    def build_status(self, result):
        """Return the Logic Manager's status in a form the template can use.

        {"is_complete": bool,
         "label": "Completed" / "Needs clarification",
         "issues": ["Task X: missing owner", ...]}   (empty if complete)
        """
        is_complete = result.get("status") in COMPLETE_STATUSES
        return {
            "is_complete": is_complete,
            "label": LABEL_COMPLETED if is_complete else LABEL_NEEDS_CLARIFICATION,
            "issues": [] if is_complete else self._issue_list(result),
        }

    def save_summary(self, handover, result, user_details):
        """Create the summary text and store it on the Handover record.

        Returns True if saved. False if the handover is not complete or saving failed.
        """
        if result.get("status") not in COMPLETE_STATUSES:
            return False
        try:
            self._store.save(handover, self._formatter.format(result, user_details))
            return True
        except OSError:
            logger.exception("Could not save the summary of handover %s", handover.pk)
            return False

    def get_summary_text(self, handover):
        """Return the saved summary text, or None if there is none."""
        if not self._store.exists(handover):
            return None
        try:
            return self._store.read(handover)
        except OSError:
            logger.exception("Could not read the summary of handover %s", handover.pk)
            return None

    def record_view(self, handover, name, employee_id):
        """Add a "viewed by" entry to the summary file. Returns True if it worked."""
        text = self.get_summary_text(handover)
        if text is None:
            return False
        try:
            entry = self._formatter.format_viewing_entry(
                name, employee_id, is_first_view=VIEWING_HEADING not in text
            )
            self._store.append(handover, entry)
            return True
        except OSError:
            logger.exception("Could not update viewing history of handover %s", handover.pk)
            return False

    # ---- private helpers --------------------------------------------------
    @staticmethod
    def _issue_list(result):
        """Turn the Logic Manager's missing_info / errors into a list of strings."""
        issues = []
        for item in result.get("missing_info", result.get("errors", [])):
            if isinstance(item, dict):
                label = item.get("task", item.get("type", "Handover"))
                details = ", ".join(item.get("errors", []))
                issues.append(f"{label}: {details}" if details else str(label))
            else:
                issues.append(str(item))
        return issues