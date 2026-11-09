from django.db import models

from .employee import Employee
from .handover import Handover

class Task(models.Model):
    TYPE_CHOICES = [
        ("outstanding", "Outstanding"),
        ("bau", "BAU"),
    ]
    FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    # handover_id: the handover this task belongs to.
    # CASCADE: if the handover is deleted, the respective tasks will be deleted too
    handover = models.ForeignKey(
        Handover,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    # code: the task ID from the AI
    code = models.CharField(max_length=10)

    # task_type: "outstanding" or "bau"
    task_type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    # title: the task name 
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # owners: the employees responsible. A task can have many owners, and an employee can own many tasks.
    owners = models.ManyToManyField(Employee, related_name="tasks_owned")

    # Outstanding tasks only
    deadline = models.DateField(null=True, blank=True)

    # BAU tasks only
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["handover", "code"]
        constraints = [
            # Note that the same code cannot be repeated within one handover
            models.UniqueConstraint(
                fields=["handover", "code"],
                name="unique_task_code_per_handover",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.title}"