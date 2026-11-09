import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.handovers.models import Employee

# part_2/apps/handovers/fixtures/employees.json
EMPLOYEES_FILE = Path(__file__).resolve().parents[2] / "fixtures" / "employees.json"


class Command(BaseCommand):
    help = "Load employees from fixtures/employees.json and create a login account for each one"

    def add_arguments(self, parser):
        # Demo password for every new account 
        parser.add_argument("--password", default="handover123")

    def handle(self, *args, **options):
        # Read the employee list; stop with a clear message if the file is missing or broken
        try:
            employees = json.loads(EMPLOYEES_FILE.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise CommandError(f"Employee file not found: {EMPLOYEES_FILE}")
        except json.JSONDecodeError as error:
            raise CommandError(f"Employee file is not valid JSON: {error}")

        User = get_user_model()
        new_count = 0

        # atomic means all employees are saved or none are if something goes wrong
        with transaction.atomic():
            for employee_id, details in employees.items():
                # Login account: username = employee ID
                user, user_is_new = User.objects.get_or_create(username=employee_id)
                if user_is_new:
                    user.set_password(options["password"])

                # Save an email when the employee fixture includes one.
                if details.get("email"):
                    user.email = details["email"].strip()

                user.save()

                # Employee row, linked to the login account
                _, employee_is_new = Employee.objects.update_or_create(
                    employee_id=employee_id,
                    defaults={
                        "name": details["name"],
                        "department": details["department"],
                        "user": user,
                    },
                )
                if employee_is_new:
                    new_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"{len(employees)} employees loaded ({new_count} new). "
            f"Log in with the employee ID as the username."
        ))