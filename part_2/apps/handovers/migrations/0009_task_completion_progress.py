import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("handovers", "0008_alter_handover_status_alter_subtask_planned_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="is_completed",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="TaskCompletion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("completion_date", models.DateField()),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="completions", to="handovers.task")),
            ],
            options={
                "ordering": ["completion_date"],
            },
        ),
        migrations.AddConstraint(
            model_name="taskcompletion",
            constraint=models.UniqueConstraint(fields=("task", "completion_date"), name="unique_task_completion_date"),
        ),
    ]
