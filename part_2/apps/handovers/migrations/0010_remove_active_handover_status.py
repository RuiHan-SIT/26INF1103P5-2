from django.db import migrations, models


def review_existing_active_handovers(apps, schema_editor):
    Handover = apps.get_model("handovers", "Handover")
    # Older records must be reviewed before they can be marked complete.
    Handover.objects.using(schema_editor.connection.alias).filter(
        status="active"
    ).update(status="needs_clarification")


class Migration(migrations.Migration):
    dependencies = [
        ("handovers", "0009_task_completion_progress"),
    ]

    operations = [
        migrations.RunPython(
            review_existing_active_handovers, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="handover",
            name="status",
            field=models.CharField(
                max_length=30,
                choices=[
                    ("completed", "Completed"),
                    ("needs_clarification", "Needs Clarification"),
                ],
                default="needs_clarification",
            ),
        ),
    ]
