from .llm_service import LLMService
from .gemini import Gemini
from .handover_coordinator import HandoverCoordinator
from .handover_service import HandoverService

__all__ = ["LLMService", "Gemini", "HandoverCoordinator", "HandoverService"]


def __getattr__(name):
    """Load AI service classes only when a caller actually needs them."""
    if name == "LLMService":
        from .llm_service import LLMService
        return LLMService
    if name == "Gemini":
        from .gemini import Gemini
        return Gemini
    if name == "HandoverCoordinator":
        from .handover_coordinator import HandoverCoordinator
        return HandoverCoordinator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
