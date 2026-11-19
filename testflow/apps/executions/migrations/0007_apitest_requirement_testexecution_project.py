import django.db.models.deletion
from django.db import migrations, models


def populate_execution_project(apps, schema_editor):
    TestExecution = apps.get_model("executions", "TestExecution")
    for execution in TestExecution.objects.select_related("test_case").all().iterator():
        execution.project_id = execution.test_case.project_id
        execution.save(update_fields=["project"])


class Migration(migrations.Migration):
    dependencies = [
        ("executions", "0006_testexecution_test_case_snapshot"),
        ("projects", "0002_project_ai_context_project_status"),
        ("requirements", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="apitest",
            name="requirement",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="api_tests", to="requirements.requirement"),
        ),
        migrations.AddField(
            model_name="testexecution",
            name="project",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="executions", to="projects.project"),
        ),
        migrations.RunPython(populate_execution_project, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="testexecution",
            name="project",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="executions", to="projects.project"),
        ),
    ]
