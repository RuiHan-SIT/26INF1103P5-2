from apps.handovers.models import Task

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
