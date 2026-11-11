from django.db import models

from .employee import Employee


class Handover(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    # This is for the employee who wrote this handover, and an employee with h/overs cannot be deleted
    created_by = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="handovers_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    completed_document = models.FileField(
            upload_to="completed_handovers/%Y/%m/%d/",
            blank=True,
        )
    
    # It's either "active" or "completed"
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # Stores extra notes from the handover that aren't tasks, then saved in a list
    important_information = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Handover {self.pk} by {self.created_by.name}"