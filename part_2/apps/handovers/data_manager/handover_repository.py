import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from django.db import DatabaseError, transaction

from apps.handovers.models import Handover, Subtask, Task, Upload

from .data_manager_error import DataManagerError

logger = logging.getLogger(__name__)


class HandoverRepository:
    """Implementation of Create, Update & Delete for Handover, Upload, Task, and Subtask rows."""

    # ---- 1. CREATE -------------------------------------------------------

    def create_upload(self, uploaded_file, employee):
        try:
            return Upload.objects.create(
                file=uploaded_file,
                original_name=uploaded_file.name,
                size_bytes=uploaded_file.size,
                uploaded_by=employee,
            )
        except DatabaseError as error:
            logger.exception("Could not save upload %s", uploaded_file.name)
            raise DataManagerError("save the uploaded file") from error

    def save_handover(self, employee, upload, processed_data, status="completed"):
        try:
            with transaction.atomic():
                handover = Handover.objects.create(
                    created_by=employee,
                    important_information=processed_data.get("important_information", []),
                    status=status,
                )

                for index, task_data in enumerate(processed_data.get("outstanding_tasks", []), start=1):
                    self._save_outstanding_task(handover, index, task_data)

                for index, task_data in enumerate(processed_data.get("bau_tasks", []), start=1):
                    self._save_bau_task(handover, index, task_data)

                upload.handover = handover
                upload.save(update_fields=["handover"])
        except DatabaseError as error:
            logger.exception("Could not save handover for employee %s", employee.pk)
            raise DataManagerError("save the handover") from error

        return handover

    def _save_outstanding_task(self, handover, index, task_data):
        task = Task.objects.create(
            handover=handover,
            code=f"OUT-{index:03d}",
            task_type="outstanding",
            title=task_data.get("task", ""),
            description=task_data.get("description", ""),
            deadline=self._parse_date(task_data.get("deadline")),
        )
        task.owners.set(task_data.get("owner_ids", []))
        self._save_subtasks(task, task_data.get("subtasks", []))

    def _save_bau_task(self, handover, index, task_data):
        task = Task.objects.create(
            handover=handover,
            code=f"BAU-{index:03d}",
            task_type="bau",
            title=task_data.get("task", ""),
            description=task_data.get("description", ""),
            frequency=task_data.get("frequency") or "",
            start_date=self._parse_date(task_data.get("start_date")),
            end_date=self._parse_date(task_data.get("end_date")),
        )
        task.owners.set(task_data.get("owner_ids", []))

    def _save_subtasks(self, task, subtasks_data):
        if not subtasks_data:
            return
        subtask_records = {}
        used_codes = set()
        fallback_index = 1

        for subtask_data in subtasks_data:
            original_id = subtask_data.get("subtask_id", f"S{fallback_index:03d}")
            code, fallback_index = self.allocate_subtask_code(
                original_id, used_codes, fallback_index
            )
            used_codes.add(code)
            subtask_records[original_id] = Subtask.objects.create(
                task=task,
                code=code,
                title=subtask_data.get("task", ""),
                planned_date=self._parse_date(subtask_data.get("planned_date")),
            )

        for subtask_data in subtasks_data:
            original_id = subtask_data.get("subtask_id")
            if original_id in subtask_records:
                deps = subtask_data.get("dependencies", [])
                valid_deps = [subtask_records[dep] for dep in deps if dep in subtask_records]
                if valid_deps:
                    subtask_records[original_id].depends_on.set(valid_deps)

    # ---- 2. UPDATE -------------------------------------------------------

    def update_subtask_status(self, subtask, is_done):
        subtask.status = "done" if is_done else "todo"
        try:
            subtask.save(update_fields=["status"])
        except DatabaseError as error:
            logger.exception("Could not update subtask %s", subtask.pk)
            raise DataManagerError("update the subtask") from error
        return subtask

    def update_handover_tasks(
        self,
        handover: Any,
        grouped_tasks: Dict[str, List[Any]],
        data: Dict[str, Any],
        is_complete: bool,
    ) -> None:
        """Atomically update saved task/subtask rows and handover status."""
        task_keys = (
            ("outstanding", "outstanding_tasks"),
            ("bau", "bau_tasks"),
        )
        with transaction.atomic():
            for task_type, data_key in task_keys:
                for task, record in zip(grouped_tasks.get(task_type, []), data.get(data_key, [])):
                    self._update_task_from_record(task, record)

            if handover.completed_document:
                handover.completed_document.delete(save=False)

            handover.important_information = [
                item
                for item in (handover.important_information or [])
                if not str(item).startswith("⚠️ Needs Clarification:")
            ]
            if is_complete:
                handover.status = "completed"
            else:
                handover.status = "needs_clarification"
                handover.important_information.append(
                    "⚠️ Needs Clarification: Some task details still need review."
                )

            handover.save(update_fields=["status", "important_information", "completed_document"])

    def _update_task_from_record(self, task: Any, record: Dict[str, Any]) -> None:
        task.title = record.get("task", "")
        task.description = record.get("description", "")

        if task.task_type == "outstanding":
            task.deadline = self._parse_date(record.get("deadline"))
        else:
            task.frequency = record.get("frequency", "")
            task.start_date = self._parse_date(record.get("start_date"))
            task.end_date = self._parse_date(record.get("end_date"))
        task.save()

        if task.task_type == "outstanding":
            self._replace_task_subtasks(task, record.get("subtasks", []))

    def _replace_task_subtasks(self, task: Any, subtask_data: List[Dict[str, Any]]) -> None:
        existing = {subtask.code: subtask for subtask in task.subtasks.all()}
        updated: Dict[str, Any] = {}

        for index, item in enumerate(subtask_data, start=1):
            code = item.get("subtask_id") or f"S{index:03d}"
            subtask = existing.get(code) or Subtask(task=task, code=code)
            subtask.title = item.get("task", "")
            subtask.planned_date = self._parse_date(item.get("planned_date"))
            subtask.save()
            updated[code] = subtask

        for subtask in existing.values():
            if subtask.code not in updated:
                subtask.delete()

        for item in subtask_data:
            subtask = updated[item.get("subtask_id")]
            dependencies = [
                updated[dep]
                for dep in item.get("dependencies", [])
                if dep in updated
            ]
            subtask.depends_on.set(dependencies)

    # ---- 3. DELETE -------------------------------------------------------

    def delete_upload(self, upload):
        upload.file.delete(save=False)
        try:
            upload.delete()
        except DatabaseError as error:
            logger.exception("Could not delete upload %s", upload.pk)
            raise DataManagerError("delete the upload") from error

    def delete_handover(self, handover: Any) -> None:
        """Delete a handover row and remove its associated upload/completed files."""
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

    # ---- Shared Persistence Helpers --------------------------------------

    @staticmethod
    def _parse_date(value: Any) -> Optional[date]:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%d/%m/%Y").date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def allocate_subtask_code(
        candidate_code: str,
        used_codes: set,
        next_code: int,
    ) -> Tuple[str, int]:
        """Ensure subtask code is <=10 chars and unique within used_codes."""
        code = str(candidate_code or f"S{next_code:03d}")
        if len(code) > 10 or code in used_codes:
            code = f"S{next_code:03d}"
            while code in used_codes:
                next_code += 1
                code = f"S{next_code:03d}"
            next_code += 1
        return code, next_code
