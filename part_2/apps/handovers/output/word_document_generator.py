from io import BytesIO

from docx import Document
from django.core.files.base import ContentFile


class CompletedHandoverDocumentGenerator:
    """Creates a downloadable Word document from a completed handover."""

    def save(self, handover):
        if handover.status != "completed":
            raise ValueError("Only completed handovers can be exported.")

        document = Document()
        document.add_heading(f"Handover H-{handover.pk:04d}", 0)
        document.add_paragraph(
            f"Created by: {handover.created_by.name} "
            f"({handover.created_by.employee_id})"
        )
        document.add_paragraph(
            f"Created on: {handover.created_at:%d %b %Y, %H:%M}"
        )

        if handover.important_information:
            document.add_heading("Important Information", level=1)
            for item in handover.important_information:
                document.add_paragraph(str(item), style="List Bullet")

        tasks = handover.tasks.prefetch_related("owners", "subtasks__depends_on")

        for task in tasks:
            heading = (
                "Outstanding Task"
                if task.task_type == "outstanding"
                else "BAU Task"
            )
            document.add_heading(heading, level=1)
            document.add_heading(task.title, level=2)

            if task.description:
                document.add_paragraph(task.description)

            owners = ", ".join(owner.name for owner in task.owners.all())
            document.add_paragraph(f"Owner(s): {owners or 'Not specified'}")

            if task.task_type == "outstanding":
                document.add_paragraph(
                    f"Deadline: {task.deadline or 'Not specified'}"
                )
            else:
                document.add_paragraph(
                    f"Frequency: {task.get_frequency_display() or 'Not specified'}"
                )
                if task.start_date:
                    document.add_paragraph(f"Start date: {task.start_date}")
                if task.end_date:
                    document.add_paragraph(f"End date: {task.end_date}")

            for subtask in task.subtasks.all():
                document.add_paragraph(
                    f"{subtask.title} (planned: {subtask.planned_date})",
                    style="List Bullet",
                )

                dependencies = list(subtask.depends_on.all())
                if dependencies:
                    names = ", ".join(item.title for item in dependencies)
                    document.add_paragraph(f"Depends on: {names}")

        file_buffer = BytesIO()
        document.save(file_buffer)

        filename = f"handover-{handover.pk:04d}.docx"
        handover.completed_document.save(
            filename,
            ContentFile(file_buffer.getvalue()),
            save=True,
        )
        return handover.completed_document