import json
import logging
from typing import Any, Dict, List, Mapping, Optional

from apps.handovers.logic_manager.handover import Handover as LogicHandover
from apps.handovers.output.word_document_generator import CompletedHandoverDocumentGenerator
from apps.handovers.services.cancellation_tracker import CancellationTracker
from apps.handovers.services.handover_coordinator import HandoverCoordinator
from apps.handovers.services.handover_mapper import HandoverDraftMapper, TASK_TYPE_SPECS

logger = logging.getLogger(__name__)


class HandoverClarificationService:
    """Manages saved handover review, clarification edits, AI suggestions, deletion, and export."""

    def __init__(
        self,
        coordinator: Optional[HandoverCoordinator] = None,
        mapper: Optional[HandoverDraftMapper] = None,
        cancellation_tracker: Optional[CancellationTracker] = None,
        document_generator: Optional[CompletedHandoverDocumentGenerator] = None,
    ):
        self._coordinator = coordinator or HandoverCoordinator()
        self._mapper = mapper or HandoverDraftMapper()
        self._cancellation = cancellation_tracker or CancellationTracker()
        self._document_generator = document_generator or CompletedHandoverDocumentGenerator()

    def attach_detail_attention(self, handover: Any, tasks: List[Any]) -> None:
        """Recheck saved details and attach field-level attention hints when clarification is needed."""
        attention: Dict[str, Any] = {}
        if handover.status == "needs_clarification":
            saved_data = self._mapper.orm_to_logic_data(handover, tasks)
            validation = LogicHandover(saved_data).process()
            attention, _ = self._mapper.build_validation_attention(tasks, validation)
        self._mapper.attach_validation_attention(tasks, attention)

    def apply_ai_suggestions(
        self,
        handover: Any,
        tasks: List[Any],
        suggested_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Validate and persist AI suggestions onto the saved handover without finalizing."""
        if not suggested_data:
            return {
                "success": False,
                "message": "Those AI suggestions are no longer available. Please ask AI to refine again.",
                "clear_suggestions": False,
            }

        grouped = self._mapper.group_tasks_by_type(tasks)
        for spec in TASK_TYPE_SPECS:
            existing_tasks = grouped[spec["task_type"]]
            suggested_tasks = suggested_data.get(spec["data_key"], [])
            if len(existing_tasks) != len(suggested_tasks):
                return {
                    "success": False,
                    "message": "AI changed the number of tasks, so its suggestions were not applied.",
                    "clear_suggestions": True,
                }
            for existing_task, suggested_task in zip(existing_tasks, suggested_tasks):
                owners = list(existing_task.owners.all())
                suggested_task["task_id"] = existing_task.code
                suggested_task["owners"] = [owner.name for owner in owners]
                suggested_task["owner_ids"] = [owner.employee_id for owner in owners]

        self._mapper.persist_clarification_edits(
            handover, tasks, suggested_data, finalize=False
        )
        return {
            "success": True,
            "message": "AI suggestions applied. Review the highlighted fields, then choose Save and recheck.",
            "clear_suggestions": True,
        }

    def request_ai_refinement(
        self,
        employee: Any,
        handover: Any,
        tasks: List[Any],
        post_data: Mapping[str, Any],
        request_token: str = "",
    ) -> Dict[str, Any]:
        """Parse form edits, ask AI for refinement, and normalize suggested subtask codes."""
        edit_data, edit_errors = self._mapper.form_to_logic_data(handover, tasks, post_data)
        if edit_errors:
            return {
                "status": "invalid_dates",
                "edit_errors": edit_errors,
                "message": "Some dates were invalid. Please correct them and save again.",
            }

        if self._cancellation.is_cancelled(employee, request_token):
            return {"status": "cancelled"}

        prompt = (
            "Review the following edited saved handover. Suggest clearer task details and sensible planned "
            "subtasks for outstanding tasks when useful. Keep exactly the same number and order of parent "
            "tasks in each task type, and keep every owner unchanged. Do not invent dates. Return the normal "
            "handover JSON structure. Draft data:\n"
            f"{json.dumps(edit_data, ensure_ascii=False)}"
        )
        result = self._coordinator.review_handover(prompt)
        if self._cancellation.is_cancelled(employee, request_token):
            return {"status": "cancelled"}

        if not result.get("success"):
            return {
                "status": "error",
                "message": f"AI could not refine this handover: {result.get('error_message', 'Unknown error')}",
            }

        suggestions = result["data"]
        grouped = self._mapper.group_tasks_by_type(tasks)
        same_task_counts = all(
            len(suggestions.get(spec["data_key"], [])) == len(grouped[spec["task_type"]])
            for spec in TASK_TYPE_SPECS
        )
        if not same_task_counts:
            return {
                "status": "error",
                "message": "AI changed the number of tasks, so its suggestions were not saved.",
            }

        for spec in TASK_TYPE_SPECS:
            for existing_task, suggestion in zip(
                grouped[spec["task_type"]], suggestions.get(spec["data_key"], [])
            ):
                owners = list(existing_task.owners.all())
                suggestion["task_id"] = existing_task.code
                suggestion["owners"] = [owner.name for owner in owners]
                suggestion["owner_ids"] = [owner.employee_id for owner in owners]

        self._mapper.normalize_ai_subtask_codes(suggestions, tasks)
        return {
            "status": "ready",
            "suggestions": suggestions,
            "message": "AI suggestions are ready. Review them below; they have not been applied yet.",
        }

    def save_clarification_edits(
        self,
        handover: Any,
        tasks: List[Any],
        post_data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Parse form edits, persist to ORM, and revalidate handover completeness."""
        edit_data, edit_errors = self._mapper.form_to_logic_data(handover, tasks, post_data)
        if edit_errors:
            return {
                "status": "invalid_dates",
                "edit_errors": edit_errors,
                "validation_messages": [],
            }

        is_complete, validation_messages = self._mapper.persist_clarification_edits(
            handover, tasks, edit_data, finalize=True
        )
        return {
            "status": "completed" if is_complete else "needs_clarification",
            "edit_errors": [],
            "validation_messages": validation_messages,
        }

    def delete_handover(self, handover: Any) -> None:
        """Delete a handover and clean up any stored upload or generated document files."""
        handover_id = handover.pk
        stored_files = [upload.file for upload in handover.uploads.all() if upload.file]
        if handover.completed_document:
            stored_files.append(handover.completed_document)

        handover.delete()
        for stored_file in stored_files:
            try:
                stored_file.delete(save=False)
            except OSError:
                logger.exception(
                    "Could not remove a stored file for deleted handover %s", handover_id
                )

    def ensure_completed_document(self, handover: Any) -> None:
        """Generate and store the Word document on first download if missing."""
        if not handover.completed_document:
            self._document_generator.save(handover)
