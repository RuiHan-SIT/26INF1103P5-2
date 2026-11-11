from django.db.models import Count

from apps.handovers.models import Employee, Handover, Subtask, Task, Upload

# Querying and filtering for the pages and the workload check
class HandoverQuery:
    # Reads data from the database for the pages (the R in CRUD)

    # Gets every task an employee owns, with its handover and subtasks loaded in one go
    def tasks_owned_by(self, employee):
        return (
            Task.objects.filter(owners=employee)
            .select_related("handover")
            .prefetch_related("subtasks__depends_on")
            .distinct()
        )

    # Gets every employee as simple dicts (ID, name, department) for owner name matching
    def employee_list(self):
        return list(Employee.objects.values("employee_id", "name", "department"))

    # Gets every employee record and it's only used when the user selects task owners
    def all_employees(self):
        return list(Employee.objects.all())

    # Gets an upload this employee hasn't saved as a handover yet (None if there isn't one)
    def pending_upload(self, upload_id, employee):
        return Upload.objects.filter(
            pk=upload_id,
            uploaded_by=employee,
            handover__isnull=True,
        ).first()

    # Gets one subtask with its task and the task's other subtasks (None if not found)
    def subtask_with_task(self, subtask_id):
        return (
            Subtask.objects.select_related("task")
            .prefetch_related("task__subtasks__depends_on")
            .filter(pk=subtask_id)
            .first()
        )

    # Searches an employee's handovers by ID , filters them by status
    def search_handovers(self, employee, search_text="", status=""):
        if employee is None:
            return Handover.objects.none()

        # Each handover also gets a count of its tasks. Essentially, newest first.
        handovers = Handover.objects.filter(created_by=employee).annotate(task_count=Count("tasks"))

        if search_text:
            number = search_text.upper().replace("H", "").replace("-", "").strip()
            if not number.isdigit():
                return Handover.objects.none()
            handovers = handovers.filter(pk=int(number))

        if status:
            handovers = handovers.filter(status=status)

        return handovers
