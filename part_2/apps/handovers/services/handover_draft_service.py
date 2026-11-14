import json
from typing import Any, Dict, List, Mapping, Optional

from apps.handovers.data_manager.data_manager_error import DataManagerError
from apps.handovers.data_manager.handover_query import HandoverQuery
from apps.handovers.data_manager.handover_repository import HandoverRepository
from apps.handovers.input_handler.handover_input_handler import HandoverInputHandler
from apps.handovers.services.cancellation_tracker import CancellationTracker
from apps.handovers.services.handover_mapper import HandoverDraftMapper
from apps.handovers.services.handover_service import HandoverService
from apps.handovers.services.workload_review_service import WorkloadReviewService


class HandoverDraftService:
    """Orchestrates handover upload, AI extraction/fallback, refinement, and initial saving."""

    def __init__(
        self,
        input_handler: Optional[HandoverInputHandler] = None,
        handover_service: Optional[HandoverService] = None,
        coordinator: Optional[Any] = None,
        repository: Optional[HandoverRepository] = None,
        query: Optional[HandoverQuery] = None,
        mapper: Optional[HandoverDraftMapper] = None,
        cancellation_tracker: Optional[CancellationTracker] = None,
    ):
        self._input_handler = input_handler or HandoverInputHandler()
        self._handover_service = handover_service or HandoverService(coordinator=coordinator)
        self._repository = repository or HandoverRepository()
        self._query = query or HandoverQuery()
        self._workload = WorkloadReviewService(query=self._query)
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
        validation = self._handover_service.validate_draft(data)["validation"]
        data["_show_fields"] = bool(data.get("_refined") or data.get("_ai_failed") or not any(
            task.get("clarification_questions") for task in data.get("outstanding_tasks", []) + data.get("bau_tasks", [])
        ))
        review_sections = self._mapper.build_review_sections(data, employees, validation)
        try:
            workload_warnings = self._workload.check(data)
            workload_error = None
        except DataManagerError as error:
            workload_warnings = []
            workload_error = str(error)
        return {
            "employee": employee,
            "review_mode": True,
            "review_sections": review_sections,
            "has_clarifications": any(
                task["clarification_questions"]
                for section in review_sections
                for task in section["tasks"]
            ),
            "ai_failed": bool(data.get("_ai_failed")),
            "validation_passed": validation["status"] == "complete",
            "workload_warnings": workload_warnings,
            "workload_review_token": self._workload.review_token(workload_warnings),
            "workload_error": workload_error,
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
            review = self._handover_service.review_document(document_text)
        except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
            review = {"ai_success": False, "error_message": str(error), "draft": {}}

        if self._cancellation.is_cancelled(employee, request_token):
            return {"status": "cancelled"}

        warning = None
        draft_data = review.get("draft", {})
        if not review.get("ai_success"):
            ai_error = review.get("error_message", "service offline")
            try:
                draft_data = self._handover_service.build_table_fallback_data(document_text)
                warning = (
                    f"Gemini AI is currently unavailable ({ai_error}). "
                    "Tasks were extracted directly from the template tables. Please review and confirm all details manually."
                )
            except Exception as fallback_err:
                return {
                    "status": "error",
                    "error_message": f"The document could not be reviewed: {review.get('error_message', fallback_err)}",
                }

        draft_data["_ai_failed"] = bool(warning)
        uploaded_file.seek(0)
        upload = self._repository.create_upload(uploaded_file, employee)
        if self._cancellation.is_cancelled(employee, request_token):
            self._repository.delete_upload(upload)
            return {"status": "cancelled"}

        return {
            "status": "ready",
            "upload": upload,
            "data": draft_data,
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
        self._mapper.apply_draft_fields(data, post_data)
        answers = self._mapper.collect_clarification_answers(data, post_data)
        missing_answers = []
        for task_type, key in [("outstanding", "outstanding_tasks"), ("bau", "bau_tasks")]:
            for index, task in enumerate(data.get(key, [])):
                questions = task.get("clarification_questions", [])
                task["_answers"] = [str(post_data.get(f"clarification_{task_type}_{index}_{i}", "")) for i in range(len(questions))]
                if questions and not any(answer.strip() for answer in task["_answers"]):
                    missing_answers.append(task.get("task", "Untitled task"))
        if missing_answers:
            return {"status": "error", "error_message": "Answer at least one question for each task: " + "; ".join(missing_answers)}
        owner_error = self._mapper.apply_owner_selections(data, post_data, self._query.all_employees())
        if owner_error:
            return {"status": "error", "error_message": owner_error}
        if not answers:
            return {
                "status": "error",
                "error_message": "Answer at least one clarification question before asking AI to refine the handover.",
            }

        try:
            self._input_handler.validate_clarification_answers(answers)
        except ValueError as error:
            return {"status": "error", "error_message": str(error)}

        try:
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
                f"{answer_text}\n\nCurrent reviewer-edited draft (preserve explicitly supplied fields):\n{json.dumps(data, ensure_ascii=False)}\n\n"
                "Revise the matching tasks using these answers. Keep the same parent tasks in the same order within each type. Do not change owners."
            )
            if self._cancellation.is_cancelled(employee, request_token):
                return {"status": "cancelled"}

            source_data = self._handover_service.build_table_fallback_data(document_text)
            for source_task, draft_task in zip(source_data["bau_tasks"], data.get("bau_tasks", [])):
                source_task["frequency"] = draft_task.get("frequency", "")
            for task in source_data["bau_tasks"]:
                for answer in answers:
                    if answer["task"] == task["task"] and "frequency" in answer["question"].lower():
                        frequency = answer["answer"].strip().lower()
                        if frequency in ["weekly", "monthly", "yearly"]:
                            task["frequency"] = frequency
            review = self._handover_service.review_document(refined_prompt, source_data=source_data)
        except (ImportError, OSError, ValueError, RuntimeError, PermissionError) as error:
            if self._cancellation.is_cancelled(employee, request_token):
                return {"status": "cancelled"}
            data["_ai_failed"] = True
            data.setdefault("important_information", []).append("AI refinement was unavailable. The Logic Manager will check the available fields.")
            return {"status": "refined", "data": data, "error_message": None}

        if self._cancellation.is_cancelled(employee, request_token):
            return {"status": "cancelled"}

        if not review.get("ai_success"):
            data["_ai_failed"] = True
            data.setdefault("important_information", []).append("AI refinement was unavailable. The Logic Manager will check the available fields.")
            return {"status": "refined", "data": data, "error_message": None}

        refined_data = review["draft"]
        for key in ["outstanding_tasks", "bau_tasks"]:
            if len(refined_data.get(key, [])) != len(data.get(key, [])):
                return {"status": "error", "error_message": "AI changed the task count. Your draft and owner selections were kept. Please retry."}
            for original, refined in zip(data.get(key, []), refined_data.get(key, [])):
                refined["task"] = original.get("task", "")
                refined["task_id"] = original.get("task_id")
                refined["owners"] = original.get("owners", [])
                refined["owner_ids"] = original.get("owner_ids", [])
                refined["_owners_confirmed"] = original.get("_owners_confirmed", False)
                refined["clarification_questions"] = []
        refined_data["_refined"] = True
        refined_data["_ai_failed"] = False
        return {"status": "refined", "data": refined_data, "error_message": None}

    def save_draft(
        self,
        employee: Any,
        upload: Any,
        data: Dict[str, Any],
        post_data: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Apply owner selections, validate via HandoverService, and persist Handover."""
        self._mapper.apply_draft_fields(data, post_data)
        if not data.get("_ai_failed") and not data.get("_refined") and any(
            task.get("clarification_questions") for task in data.get("outstanding_tasks", []) + data.get("bau_tasks", [])
        ):
            return {"status": "invalid", "error_message": "Answer at least one question per task and refine with AI before saving.", "missing_reasons": []}
        owner_error = self._mapper.apply_owner_selections(
            data, post_data, self._query.all_employees()
        )
        if owner_error:
            return {"status": "invalid", "error_message": owner_error, "missing_reasons": []}

        check = self._handover_service.validate_draft(data)
        processed = check["validation"]

        if processed["status"] != "complete" and not data.get("_ai_failed"):
            return {"status": "invalid", "error_message": "Correct the highlighted fields before confirming this handover.", "missing_reasons": self._format_missing_reasons(processed, False)}
        try:
            workload_warnings = self._workload.check(data)
        except DataManagerError as error:
            return {"status": "error", "error_message": str(error), "missing_reasons": []}
        if workload_warnings and post_data.get("acknowledge_workload") != self._workload.review_token(workload_warnings):
            return {"status": "invalid", "error_message": "Review the workload warning below. Adjust the schedule or acknowledge it to save anyway.", "missing_reasons": []}
        if processed["status"] == "complete":
            try:
                handover = self._repository.save_handover(
                    employee, upload, processed, status="completed"
                )
            except DataManagerError as error:
                return {"status": "error", "error_message": str(error), "missing_reasons": []}
            return {"status": "completed", "handover": handover, "missing_reasons": []}

        save_data = check["task_records"]
        missing_reasons = self._format_missing_reasons(processed, False)
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
