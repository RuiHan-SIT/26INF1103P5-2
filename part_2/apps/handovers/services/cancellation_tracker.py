from uuid import UUID

from django.core.cache import cache

CANCEL_REQUEST_TIMEOUT = 60 * 15


class CancellationTracker:
    """Tracks in-flight AI processing cancellations per employee and request token."""

    def __init__(self, cache_backend=None, timeout: int = CANCEL_REQUEST_TIMEOUT):
        self._cache = cache_backend or cache
        self._timeout = timeout

    @staticmethod
    def is_valid_token(value: str) -> bool:
        """Return True when value is a valid UUID string."""
        try:
            UUID(value)
            return True
        except (TypeError, ValueError, AttributeError):
            return False

    @staticmethod
    def _cache_key(employee, request_token: str) -> str:
        return f"handover-cancel:{employee.pk}:{request_token}"

    def cancel(self, employee, request_token: str) -> bool:
        """Mark a request token as cancelled for the given employee."""
        if not employee or not self.is_valid_token(request_token):
            return False
        self._cache.set(
            self._cache_key(employee, request_token),
            True,
            timeout=self._timeout,
        )
        return True

    def is_cancelled(self, employee, request_token: str) -> bool:
        """Check whether the given employee/token pair has been cancelled."""
        if not employee or not self.is_valid_token(request_token):
            return False
        return bool(self._cache.get(self._cache_key(employee, request_token)))
