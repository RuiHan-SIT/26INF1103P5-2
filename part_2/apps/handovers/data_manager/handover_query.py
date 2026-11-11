from apps.handovers.models import Employee, Task

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
