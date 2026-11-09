from django.conf import settings
from django.db import models


# Representing a valid  employee who can log in 
class Employee(models.Model):
    # The 7-digit employee ID is the unique key for each registered employee
    employee_id = models.CharField(max_length=7, primary_key=True)
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)

    # For the Login: if the account is ever removed, the employee record is kept.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee",
    )
    
    # Holds settings for the table
    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        return f"{self.employee_id} - {self.name}"