from typing import Any, Dict, List, Mapping, Optional

from apps.handovers.data_manager.data_manager_error import DataManagerError
from apps.handovers.data_manager.handover_query import HandoverQuery
from apps.handovers.data_manager.handover_repository import HandoverRepository
from apps.handovers.input_handler.handover_input_handler import HandoverInputHandler
from apps.handovers.logic_manager.handover import Handover as LogicHandover
from apps.handovers.services.cancellation_tracker import CancellationTracker
from apps.handovers.services.handover_coordinator import HandoverCoordinator
from apps.handovers.services.handover_mapper import HandoverDraftMapper


class HandoverDraftService:
    """Orchestrates handover upload, AI extraction/fallback, refinement, and initial saving."""

    def __init__(
        self,
        input_handler: Optional[HandoverInputHandler] = None,
        coordinator: Optional[HandoverCoordinator] = None,
        repository: Optional[HandoverRepository] = None,
        query: Optional[HandoverQuery] = None,
        mapper: Optional[HandoverDraftMapper] = None,
        cancellation_tracker: Optional[CancellationTracker] = None,
    ):
        self._input_handler = input_handler or HandoverInputHandler()
        self._coordinator = coordinator or HandoverCoordinator()
        self._repository = repository or HandoverRepository()
        self._query = query or HandoverQuery()
        self._mapper = mapper or HandoverDraftMapper()
        self._cancellation = cancellation_tracker or CancellationTracker()

    def build_review_context(
        self,
        employee: Any,
        upload: Any,
        data: Dict[str, Any],
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build template context for rendering the draft review screen."""
        employees = self._query.employee_list()
        review_sections = self._mapper.build_review_sections(data, employees)
        return {
            "employee": employee,
            "review_mode": True,
            "review_sections": review_sections,
            "has_clarifications": any(
                task["clarification_questions"]
                for section in review_sections
                for task in section["tasks"]
            ),
            "review_error": error_message,
            "uploaded_filename": upload.original_name if upload else "",
            "important_information": data.get("important_information", []),
        }

    def upload_and_review(
        self,
        employee: Any,
        uploaded_file: Any,
        request_token: str = "",
    ) -> Dict[str, Any]:
        """Read uploaded document, run AI extraction (or table fallback), and persist Upload."""
        if not employee:
            return {
                "status": "error",
                "error_message": "Your employee profile could not be found.",
            }

        try:
            document_text = self._input_handler.process_upload(uploaded_file)
        except ValueError as error:
            return {"status": "error", "error_message": str(error)}

        if self._cancellation.is_cancelled(employee, request_token):
            return {"status": "cancelled"}

        try:
            result = self._coordinator.review_handover(document_text)
        except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
            result = {"success": False, "error_message": str(error)}

        if self._cancellation.is_cancelled(employee, request_token):
            return {"status": "cancelled"}

        warning = None
        if not result.get("success"):
            ai_error = result.get("error_message", "service offline")
            try:
                fallback_data = HandoverCoordinator.build_table_fallback_data(document_text)
                result = {"success": True, "data": fallback_data}
                warning = (
                    f"Gemini AI is currently unavailable ({ai_error}). "
                    "Tasks were extracted directly from the template tables. Please review and confirm all details manually."
                )
            except Exception as fallback_err:
                return {
                    "status": "error",
                    "error_message": f"The document could not be reviewed: {result.get('error_message', fallback_err)}",
                }

        uploaded_file.seek(0)
        upload = self._repository.create_upload(uploaded_file, employee)
        if self._cancellation.is_cancelled(employee, request_token):
            self._repository.delete_upload(upload)
            return {"status": "cancelled"}

        return {
            "status": "ready",
            "upload": upload,
            "data": result["data"],
            "warning": warning,
            "error_message": None,
        }

    def refine_draft(
        self,
        employee: Any,
        upload: Any,
        data: Dict[str, Any],
        post_data: Mapping[str, Any],
        request_token: str = "",
    ) -> Dict[str, Any]:
        """Re-run AI review incorporating reviewer answers to clarification questions."""
        answers = self._mapper.collect_clarification_answers(data, post_data)
        if not answers:
            return {
                "status": "error",
                "error_message": "Answer at least one clarification question before asking AI to refine the handover.",
            }

        try:
            self._input_handler.validate_clarification_answers(answers)
            upload.file.open("rb")
            try:
                document_text = self._input_handler.process_upload(upload.file)
            finally:
                upload.file.close()

            answer_text = "\n".join(
                f"Task: {item['task']}\nQuestion: {item['question']}\nReviewer answer: {item['answer']}"
                for item in answers
            )
            refined_prompt = (
                f"{document_text}\n\n"
                "REVIEWER ANSWERS TO CLARIFICATION QUESTIONS:\n"
                f"{answer_text}\n\n"
                "Revise the matching tasks using these answers."
            )
            if self._cancellation.is_cancelled(employee, request_token):
                return {"status": "cancelled"}

            source_data = HandoverCoordinator.build_table_fallback_data(document_text)
            for task in source_data["bau_tasks"]:
                for answer in answers:
                    if answer["task"] == task["task"] and "frequency" in answer["question"].lower():
                        frequency = answer["answer"].strip().lower()
                        if frequency in ["weekly", "monthly", "yearly"]:
                            task["frequency"] = frequency
            result = self._coordinator.review_handover(refined_prompt, source_data=source_data)
        except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
            if self._cancellation.is_cancelled(employee, request_token):
                return {"status": "cancelled"}
            return {
                "status": "error",
                "error_message": f"Could not refine the handover: {error}",
            }

        if self._cancellation.is_cancelled(employee, request_token):
            return {"status": "cancelled"}

        if not result.get("success"):
            return {
                "status": "error",
                "error_message": f"Could not refine the handover: {result.get('error_message')}",
            }

        return {"status": "refined", "data": result["data"], "error_message": None}

    def save_draft(
        self,
        employee: Any,
        upload: Any,
        data: Dict[str, Any],
        post_data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Apply owner selections, validate via LogicHandover, and persist Handover."""
        owner_error = self._mapper.apply_owner_selections(
            data, post_data, self._query.all_employees()
        )
        if owner_error:
            return {"status": "invalid", "error_message": owner_error, "missing_reasons": []}

        logic_data = HandoverCoordinator.strip_clarification_questions(data)
        logic = LogicHandover(logic_data)
        processed = logic.process()

        has_questions = any(
            task.get("clarification_questions")
            for task in data.get("outstanding_tasks", []) + data.get("bau_tasks", [])
        )

        if processed["status"] == "complete" and not has_questions:
            try:
                handover = self._repository.save_handover(
                    employee, upload, processed, status="completed"
                )
            except DataManagerError as error:
                return {"status": "error", "error_message": str(error), "missing_reasons": []}
            return {"status": "completed", "handover": handover, "missing_reasons": []}

        save_data = logic.get_task_records()
        missing_reasons = self._format_missing_reasons(processed, has_questions)
        if missing_reasons:
            save_data.setdefault("important_information", []).append(
                f"⚠️ Needs Clarification: Handover saved with pending items: {'; '.join(missing_reasons)}"
            )

        try:
            handover = self._repository.save_handover(
                employee, upload, save_data, status="needs_clarification"
            )
        except DataManagerError as error:
            return {"status": "error", "error_message": str(error), "missing_reasons": []}

        return {
            "status": "needs_clarification",
            "handover": handover,
            "missing_reasons": missing_reasons,
            "error_message": None,
        }

    def cancel_draft(self, upload: Any) -> None:
        """Delete a pending Upload record if one exists."""
        if upload is not None:
            self._repository.delete_upload(upload)

    @staticmethod
    def _format_missing_reasons(processed: Dict[str, Any], has_questions: bool) -> List[str]:
        missing_reasons: List[str] = []
        if processed["status"] != "complete":
            for err in processed.get("errors", []):
                if isinstance(err, dict):
                    task_name = err.get("task", f"Task {err.get('index', '')}")
                    reasons = ", ".join(err.get("errors", []))
                    missing_reasons.append(f"{task_name} ({reasons})")
                else:
                    missing_reasons.append(str(err))
        if has_questions:
            missing_reasons.append("Unanswered clarification questions remain")
        return missing_reasons
