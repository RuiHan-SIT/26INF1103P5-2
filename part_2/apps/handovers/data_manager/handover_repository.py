from datetime import datetime

from django.db import transaction

from apps.handovers.models import Handover, Subtask, Task, Upload


# Implementation of Create, Update & Delete: turns the shared dictionary into rows prior to saving

class HandoverRepository:
    # Saves handovers into the database
    #=======================================
    # CREATE
    #=======================================

    # Saves a newly uploaded file and its details (before it becomes a handover)
    def create_upload(self, uploaded_file, employee):
        return Upload.objects.create(
            file=uploaded_file,
            original_name=uploaded_file.name,
            size_bytes=uploaded_file.size,
            uploaded_by=employee,
        )

    # Essentially saves an approved h/over with all it's tasks and subtasks, then links its upload
    def save_handover(self, employee, upload, processed_data):
        # After the logic manager has validated, the said h/over will be saved
        # Everything inside the "with" block is saved together, or nothing is saved if an error happens
        with transaction.atomic():
            handover = Handover.objects.create(
                created_by=employee,
                important_information=processed_data["important_information"],
            )

            for index, task_data in enumerate(processed_data["outstanding_tasks"], start=1):
                self._save_outstanding_task(handover, index, task_data)

            for index, task_data in enumerate(processed_data["bau_tasks"], start=1):
                self._save_bau_task(handover, index, task_data)

            upload.handover = handover
            upload.save(update_fields=["handover"])

        return handover

    # ---- private methods

    # Saves one outstanding task (with a deadline) along with its subtasks
    def _save_outstanding_task(self, handover, index, task_data):
        task = Task.objects.create(
            handover=handover,
            code=f"OUT-{index:03d}",
            task_type="outstanding",
            title=task_data["task"],
            description=task_data["description"],
            deadline=self._parse_date(task_data["deadline"]),
        )
        task.owners.set(task_data["owner_ids"])
        self._save_subtasks(task, task_data["subtasks"])
        
    # Saves one BAU routine task with its recurring frequency and dates
    def _save_bau_task(self, handover, index, task_data):
        task = Task.objects.create(
            handover=handover,
            code=f"BAU-{index:03d}",
            task_type="bau",
            title=task_data["task"],
            description=task_data["description"],
            frequency=task_data["frequency"],
            start_date=self._parse_date(task_data["start_date"]),
            end_date=self._parse_date(task_data["end_date"]),
        )
        task.owners.set(task_data["owner_ids"])
        
    # Saves a task's subtasks, then links whichever subtask depends on which
    def _save_subtasks(self, task, subtasks_data):
        # Saving the subtask
        subtask_records = {}
        used_codes = set()
        fallback_index = 1

        for subtask_data in subtasks_data:
            original_id = subtask_data["subtask_id"]
            code = original_id

            # If the AI's id is too long or repeated, give it a new one like "S002"
            if len(code) > 10 or code in used_codes:
                code = f"S{fallback_index:03d}"
                while code in used_codes:
                    fallback_index += 1
                    code = f"S{fallback_index:03d}"
                fallback_index += 1

            used_codes.add(code)
            subtask_records[original_id] = Subtask.objects.create(
                task=task,
                code=code,
                title=subtask_data["task"],
                planned_date=self._parse_date(subtask_data["planned_date"]),
            )

        # Then link the dependencies, now that every subtask exists
        for subtask_data in subtasks_data:
            subtask_records[subtask_data["subtask_id"]].depends_on.set(
                [subtask_records[dependency] for dependency in subtask_data["dependencies"]]
            )

    #=======================================
    # UPDATE
    #=======================================

    # Ticks a subtask as done, or back to to-do
    def update_subtask_status(self, subtask, is_done):
        subtask.status = "done" if is_done else "todo"
        subtask.save(update_fields=["status"])
        return subtask

    #=======================================
    # DELETE
    #=======================================

    # Deletes a cancelled upload: removes the file from media/ and its database row
    def delete_upload(self, upload):
        upload.file.delete(save=False)
        upload.delete()
        
        
    def _parse_date(self, value):
        # Turns a written date (string) into a real date
        if not value:
            return None
        return datetime.strptime(value, "%d/%m/%Y").date()