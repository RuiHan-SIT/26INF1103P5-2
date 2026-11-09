import copy
import logging
from typing import Any, Dict, Optional

from .llm_service import LLMService
from .gemini import Gemini
from utils.prompt import HANDOVER_REVIEW_PROMPT
from utils.json_helper import clean_llm_json
from apps.schema import validate_and_normalize_handover

logger = logging.getLogger(__name__)


class HandoverCoordinator:
    """
    Coordinates AI-driven review and normalization of handover documents.

    Responsibilities (SRP):
    - Accepts pre-validated, PII-sanitized handover text/content.
    - Sends structured prompts to the LLM service (Gemini).
    - Delegates raw JSON parsing and cleanup to utils.json_helper.
    - Delegates schema validation and normalization to apps.schema.
    - Returns a clean fallback structure if AI extraction fails.
    """

    FALLBACK_DATA = {
        "outstanding_tasks": [],
        "bau_tasks": [],
        "important_information": []
    }

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Dependency injection for LLM service.
        Defaults to Gemini if none is provided.
        """
        self.__llm_service = llm_service or Gemini()

    @property
    def llm_service(self) -> LLMService:
        """Returns the configured LLM service instance."""
        return self.__llm_service

    def review_handover(self, handover_content: str) -> Dict[str, Any]:
        """
        Coordinates submitting sanitized handover text to Gemini for review,
        cleaning the response, and validating the schema.

        :param handover_content: sanitized handover text or table summary.
        :return: Standardized result dict with success flag, data, or error message.
        """
        if not handover_content or not handover_content.strip():
            return {
                "success": False,
                "data": copy.deepcopy(self.FALLBACK_DATA),
                "error_message": "Handover content cannot be empty."
            }

        try:
            # 1. Orchestrate LLM call from GEMINI.py
            raw_response = self.__llm_service.generate(
                prompt=handover_content,
                system_instruction=HANDOVER_REVIEW_PROMPT
            )

            # 2. Delegate JSON cleaning & repair
            parsed_data = clean_llm_json(raw_response)

            # 3. Delegate schema validation & normalization
            normalized_data = validate_and_normalize_handover(parsed_data)

            return {
                "success": True,
                "data": normalized_data,
                "error_message": None
            }

        except (ValueError, RuntimeError, PermissionError) as err:
            logger.warning("Handover review processing failed: %s", err)
            return {
                "success": False,
                "data": copy.deepcopy(self.FALLBACK_DATA),
                "error_message": str(err)
            }
        except Exception as err:
            logger.exception("Unexpected error during handover coordination: %s", err)
            return {
                "success": False,
                "data": copy.deepcopy(self.FALLBACK_DATA),
                "error_message": f"An unexpected error occurred during handover processing: {err}"
            }

    @staticmethod
    def strip_clarification_questions(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Utility method to strip clarification_questions from tasks before
        passing the dictionary to Handover logic manager or database models.
        """
        cleaned_outstanding = []
        for task in data.get("outstanding_tasks", []):
            task_copy = dict(task)
            task_copy.pop("clarification_questions", None)
            cleaned_outstanding.append(task_copy)

        cleaned_bau = []
        for task in data.get("bau_tasks", []):
            task_copy = dict(task)
            task_copy.pop("clarification_questions", None)
            cleaned_bau.append(task_copy)

        return {
            "outstanding_tasks": cleaned_outstanding,
            "bau_tasks": cleaned_bau,
            "important_information": list(data.get("important_information", []))
        }
