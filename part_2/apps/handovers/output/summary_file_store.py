# Saves, reads and adds to the summary file of a handover
# The file is kept in the Handover model's "completed_document" field, so Django
# decides where it lives on disk (MEDIA_ROOT). Only this class touches that file.


class SummaryFileStore:
    """Handles the summary file of ONE Handover record."""

    def save(self, handover, text):
        """Store the summary text as the handover's file."""
        from django.core.files.base import ContentFile  
        filename = f"handover_{handover.pk}_summary.txt"
        handover.completed_document.save(filename, ContentFile(text.encode("utf-8")), save=True)

    def exists(self, handover):
        return bool(handover.completed_document)

    def read(self, handover):
        """Return the text of the summary file."""
        with handover.completed_document.open("rb") as file:
            return file.read().decode("utf-8")

    def append(self, handover, extra_text):
        """Add text to the end of the file (used for the "viewed by" log)."""
        new_text = self.read(handover) + extra_text
        # Replace the old file with a new one that has the extra text
        handover.completed_document.delete(save=False)
        self.save(handover, new_text)