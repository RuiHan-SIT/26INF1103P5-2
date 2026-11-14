import copy
import logging
from typing import Any, Dict, Optional

from .llm_service import LLMService
from .gemini import Gemini
from utils.prompt import HANDOVER_REVIEW_PROMPT
from utils.json_helper import JsonHelper
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
            parsed_data = JsonHelper.clean_llm_json(raw_response)

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
    def strip_clarification_questions(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Utility method to strip clarification_questions from tasks before
        passing the dictionary to Handover logic manager or database models.
        Works seamlessly whether clarification_questions exist or not.
        """
        if not data or not isinstance(data, dict):
            return {
                "outstanding_tasks": [],
                "bau_tasks": [],
                "important_information": []
            }

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

    @classmethod
    def build_table_fallback_data(cls, document_text: str) -> Dict[str, Any]:
        """
        Parses structured task fields from DocumentReader text output
        when Gemini AI service is unavailable.
        """
        data = {
            "outstanding_tasks": [],
            "bau_tasks": [],
            "important_information": [
                "⚠️ Gemini AI was unavailable during document upload. Tasks were extracted directly from document tables. Please review and confirm all details manually."
            ]
        }

        if not document_text:
            return data

        lines = [line.strip() for line in document_text.splitlines() if line.strip()]
        current_task = {}
        tasks = []

        for line in lines:
            task_header = line[:-1].strip().lower() if line.endswith(":") else ""
            task_number = task_header[5:].strip() if task_header.startswith("task ") else ""
            if task_number and all(part.isdigit() for part in task_number.split(".")):
                if current_task and current_task.get("task"):
                    tasks.append(current_task)
                current_task = {}
                continue
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip().lower()
                val = val.strip()
                if key == "task name":
                    current_task["task"] = val
                elif key == "description":
                    current_task["description"] = val
                elif key.startswith("task owner"):
                    current_task["owners"] = [o.strip() for o in val.split(",") if o.strip()]
                elif key == "task type":
                    current_task["task_type"] = val.lower()
                elif key == "deadline":
                    current_task["deadline"] = val
                elif key == "frequency":
                    current_task["frequency"] = val
                elif key == "start date":
                    current_task["start_date"] = val
                elif key == "end date":
                    current_task["end_date"] = val

        if current_task and current_task.get("task"):
            tasks.append(current_task)

        for t in tasks:
            task_type = t.get("task_type", "").strip().lower()
            owners = t.get("owners", [])
            start_date = t.get("start_date") or None
            end_date = t.get("end_date") or None
            frequency = (t.get("frequency") or "").strip().lower()

            if "bau" in task_type or "recur" in task_type:
                is_bau = True
            elif "one-off" in task_type or "one off" in task_type or "outstanding" in task_type:
                is_bau = False
            else:
                is_bau = bool(frequency or start_date or end_date)

            if is_bau:
                data["bau_tasks"].append({
                    "task": t.get("task", "Untitled Task"),
                    "description": t.get("description", ""),
                    "owners": owners,
                    "frequency": frequency,
                    "start_date": start_date,
                    "end_date": end_date,
                    "clarification_questions": [],
                })
            else:
                data["outstanding_tasks"].append({
                    "task": t.get("task", "Untitled Task"),
                    "description": t.get("description", ""),
                    "owners": owners,
                    "deadline": t.get("deadline") or None,
                    "subtasks": [],
                    "clarification_questions": [],
                })

        return data
