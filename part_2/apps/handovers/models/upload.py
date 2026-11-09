from django.db import models

from .employee import Employee
from .handover import Handover


class Upload(models.Model):
    # The handover made from this file.
    # It will be empty at first because the file is uploaded before the AI creates the handover.
    # CASCADE = if the handover is deleted, this upload record is deleted too.
   
    # handover_id
    handover = models.ForeignKey(
        Handover,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="uploads",
    )

    # file: The said file
    file = models.FileField(upload_to="uploads/%Y/%m/%d/", max_length=255)

    # original_name: The said file's name
    original_name = models.CharField(max_length=255)

    # size_bytes: File size in bytes
    size_bytes = models.PositiveIntegerField()

    # uploaded_by_id: The employee who uploaded the said file
    uploaded_by = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="uploads",
    )

    # uploaded_at: Auto filled
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Newest upload first
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_name