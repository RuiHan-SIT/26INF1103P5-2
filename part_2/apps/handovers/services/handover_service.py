import copy
from typing import Any, Dict, Optional

from apps.handovers.services.handover_coordinator import HandoverCoordinator
from apps.handovers.logic_manager.handover import Handover


class HandoverService:
    """
    Coordinates the 2-pass Handover Review & Clarification lifecycle.

    Responsibilities (SRP):
    - Pass 1 (review_document): Gets AI extraction (or clean fallback from
      HandoverCoordinator) and runs initial Handover logic validation while
      preserving clarification_questions.
    - Pass 2 (update_draft_task): Applies user edits/clarifications to a draft
      task and re-validates via Handover logic manager without re-calling AI.
    """

    def __init__(self, coordinator: Optional[HandoverCoordinator] = None):
        """
        Dependency injection for HandoverCoordinator.
        Defaults to a standard HandoverCoordinator instance if none is provided.
        """
        self.__coordinator = coordinator or HandoverCoordinator()

    @property
    def coordinator(self) -> HandoverCoordinator:
        """Returns the configured HandoverCoordinator instance."""
        return self.__coordinator

    def review_document(self, handover_text: str, source_data=None) -> Dict[str, Any]:
        """
        Pass 1: Extracts tasks via HandoverCoordinator and validates them
        with Handover logic manager.
        """
        if source_data is None:
            ai_result = self.__coordinator.review_handover(handover_text)
        else:
            ai_result = self.__coordinator.review_handover(handover_text, source_data=source_data)
        raw_draft = ai_result.get("data", HandoverCoordinator.FALLBACK_DATA)
        draft_data = copy.deepcopy(raw_draft)

        # Strip AI-only clarification_questions before passing to Handover logic manager
        cleaned_data = HandoverCoordinator.strip_clarification_questions(draft_data)
        validation_result = Handover(cleaned_data).process()

        return {
            "ai_success": bool(ai_result.get("success")),
            "error_message": ai_result.get("error_message"),
            "draft": draft_data,             # Keep in session (has clarification_questions)
            "validation": validation_result  # {"status": "complete"|"incomplete", ...}
        }

    def validate_draft(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strips AI-only clarification_questions and runs Handover logic validation,
        returning both the processed validation status and normalized task records.
        """
        cleaned_data = HandoverCoordinator.strip_clarification_questions(draft_data)
        handover = Handover(cleaned_data)
        return {
            "validation": handover.process(),
            "task_records": handover.get_task_records(),
        }

    def build_table_fallback_data(self, document_text: str) -> Dict[str, Any]:
        """Extracts fallback handover tasks directly from template tables when AI is offline."""
        return HandoverCoordinator.build_table_fallback_data(document_text)

    def update_draft_task(
        self,
        draft_data: Dict[str, Any],
        task_type: str,
        task_id: str,
        task_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Pass 2: Applies user edits/clarifications to a task in the draft
        and re-runs Handover logic validation (without calling AI again).
        """
        cleaned_data = HandoverCoordinator.strip_clarification_questions(draft_data)
        handover = Handover(cleaned_data)

        # Validate and apply the edit using logic_manager's update_task()
        update_result = handover.update_task(task_type, task_id, task_changes)

        # If the task edit was valid, sync the changes back into draft_data
        # and clear clarification_questions for that task since the user reviewed it
        updated_draft = copy.deepcopy(draft_data)
        if update_result["status"] == "updated":
            task_list_key = "outstanding_tasks" if task_type == "outstanding" else "bau_tasks"
            for index, task in enumerate(updated_draft.get(task_list_key, [])):
                if task.get("task_id") == task_id:
                    updated_task = dict(update_result["task"])
                    updated_task["clarification_questions"] = []
                    updated_draft[task_list_key][index] = updated_task
                    break

        return {
            "update_result": update_result,       # {"status": "updated"|"invalid"|"not_found", ...}
            "draft": updated_draft,               # Updated draft for session
            "validation": handover.process()      # Re-check if whole handover is now "complete"
        }
