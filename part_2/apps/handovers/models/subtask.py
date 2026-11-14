from django.db import models

from .task import Task


class Subtask(models.Model):
    STATUS_CHOICES = [
        ("todo", "To do"),
        ("done", "Done"),
    ]
    SOURCE_CHOICES = [
        ("ai", "AI suggested"),
        ("user", "Changed by user"),
        ("fallback", "Fallback (AI failed)"),
    ]

    # task_id: the task this subtask belongs to.
    # CASCADE = if the task is deleted, the respective subtasks are deleted too.
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="subtasks",
    )

    # code: the subtask ID from the AI
    code = models.CharField(max_length=10)

    # title: the subtask name 
    title = models.CharField(max_length=255)

    # planned_date: the day this subtask appears on the calendar
    planned_date = models.DateField(null=True, blank=True)

    # status: ticked off or not
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="todo")

    # source: who set the planned date
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="ai")

    # depends_on: subtasks that must be done before this one
    depends_on = models.ManyToManyField(
        "self",
        # dependencies can only go one way
        symmetrical=False,
        
        blank=True,
        related_name="needed_by",
    )

    class Meta:
        # Earliest date first, so the calendar is in order
        ordering = ["planned_date", "code"]
        constraints = [
            # The same code cannot be repeated within one task
            models.UniqueConstraint(
                fields=["task", "code"],
                name="unique_subtask_code_per_task",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.title}"