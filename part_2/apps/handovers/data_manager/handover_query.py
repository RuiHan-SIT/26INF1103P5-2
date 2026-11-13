import logging

from django.db import DatabaseError
from django.db.models import Count

from apps.handovers.models import Employee, Handover, Subtask, Task, Upload

from .data_manager_error import DataManagerError

logger = logging.getLogger(__name__)


# Querying and filtering for the pages and the workload check
class HandoverQuery:
    # Reads data from the database for the pages (the R in CRUD)
    # Each read is wrapped so a missing, corrupt or locked database gives a DataManagerError

    # Gets every task an employee owns, with its handover and subtasks loaded in one go
    def tasks_owned_by(self, employee):
        try:
            # list() runs the query now, so any database error is caught here
            return list(
                Task.objects.filter(owners=employee)
                .select_related("handover")
                .prefetch_related("subtasks__depends_on")
                .distinct()
            )
        except DatabaseError as error:
            logger.exception("Could not load tasks for employee %s", employee.pk)
            raise DataManagerError("load your tasks") from error

    # Gets every employee as simple dicts (ID, name, department) for owner name matching
    def employee_list(self):
        try:
            return list(Employee.objects.values("employee_id", "name", "department"))
        except DatabaseError as error:
            logger.exception("Could not load the employee list")
            raise DataManagerError("load the employee list") from error

    # Gets every employee record and it's only used when the user selects task owners
    def all_employees(self):
        try:
            return list(Employee.objects.all())
        except DatabaseError as error:
            logger.exception("Could not load employees")
            raise DataManagerError("load the employee list") from error

    # Gets an upload this employee hasn't saved as a handover yet (None if there isn't one)
    def pending_upload(self, upload_id, employee):
        try:
            return Upload.objects.filter(
                pk=upload_id,
                uploaded_by=employee,
                handover__isnull=True,
            ).first()
        except DatabaseError as error:
            logger.exception("Could not load upload %s", upload_id)
            raise DataManagerError("load your uploaded file") from error

    # Gets one subtask with its task and the task's other subtasks (None if not found)
    def subtask_with_task(self, subtask_id):
        try:
            return (
                Subtask.objects.select_related("task")
                .prefetch_related("task__subtasks__depends_on")
                .filter(pk=subtask_id)
                .first()
            )
        except DatabaseError as error:
            logger.exception("Could not load subtask %s", subtask_id)
            raise DataManagerError("load the subtask") from error

    # Searches an employee's handovers by ID , filters them by status
    def search_handovers(self, employee, search_text="", status=""):
        if employee is None:
            return []

        # Each handover also gets a count of its tasks. Essentially, newest first.
        handovers = Handover.objects.filter(created_by=employee).annotate(task_count=Count("tasks"))

        if search_text:
            number = search_text.upper().replace("H", "").replace("-", "").strip()
            if not number.isdigit():
                return []
            handovers = handovers.filter(pk=int(number))

        if status:
            handovers = handovers.filter(status=status)

        try:
            # list() runs the query now, so any database error is caught here
            return list(handovers)
        except DatabaseError as error:
            logger.exception("Could not search handovers for employee %s", employee.pk)
            raise DataManagerError("load your handovers") from error

    # Gets one of this employee's handovers that can be downloaded (None if not found)
    def downloadable_handover(self, handover_id, employee):
        try:
            return Handover.objects.filter(
                pk=handover_id,
                created_by=employee,
                status__in=["completed", "needs_clarification"],
            ).first()
        except DatabaseError as error:
            logger.exception("Could not load handover %s", handover_id)
            raise DataManagerError("load the handover") from error
