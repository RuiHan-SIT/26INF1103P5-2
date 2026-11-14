from apps.handovers.data_manager.handover_query import HandoverQuery

PENDING_UPLOAD_KEY = "pending_handover_upload_id"
PENDING_DATA_KEY = "pending_handover_data"


class PendingDraftSession:
    """Manages pending handover draft state stored in the user's HTTP session."""

    def __init__(self, request, query=None):
        self._session = request.session
        self._query = query or HandoverQuery()

    def load(self, employee):
        """Return (upload, data) if a valid pending draft exists, else (None, None)."""
        upload_id = self._session.get(PENDING_UPLOAD_KEY)
        data = self._session.get(PENDING_DATA_KEY)
        upload = self._query.pending_upload(upload_id, employee)
        if not upload or not data:
            self.clear()
            return None, None
        return upload, data

    def save(self, upload, data):
        """Store pending upload ID and extracted draft data in the session."""
        self._session[PENDING_UPLOAD_KEY] = upload.pk
        self._session[PENDING_DATA_KEY] = data

    def update_data(self, data):
        """Replace the pending draft data in the session."""
        self._session[PENDING_DATA_KEY] = data

    def clear(self):
        """Remove pending draft keys from the session."""
        self._session.pop(PENDING_UPLOAD_KEY, None)
        self._session.pop(PENDING_DATA_KEY, None)
