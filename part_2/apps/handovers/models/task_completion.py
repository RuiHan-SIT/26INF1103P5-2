from django.db import models

from .task import Task


class TaskCompletion(models.Model):
    # One completed date for a recurring BAU task.
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    completion_date = models.DateField()

    class Meta:
        ordering = ["completion_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "completion_date"],
                name="unique_task_completion_date",
            ),
        ]

    def __str__(self):
        return f"{self.task.code} completed on {self.completion_date}"
