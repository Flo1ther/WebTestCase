import django.db.models.deletion
from django.db import migrations, models


def populate_defect_project_and_requirement(apps, schema_editor):
    Defect = apps.get_model("defects", "Defect")
    for defect in Defect.objects.select_related("test_case").all().iterator():
        defect.project_id = defect.test_case.project_id
        defect.requirement_id = defect.test_case.requirement_id
        defect.save(update_fields=["project", "requirement"])


class Migration(migrations.Migration):
    dependencies = [
        ("defects", "0003_defect_actual_result_defect_environment_and_more"),
        ("projects", "0002_project_ai_context_project_status"),
        ("requirements", "0001_initial"),
        ("test_cases", "0005_testcase_requirement"),
    ]

    operations = [
        migrations.AddField(
            model_name="defect",
            name="project",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="defects", to="projects.project"),
        ),
        migrations.AddField(
            model_name="defect",
            name="requirement",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="defects", to="requirements.requirement"),
        ),
        migrations.RunPython(populate_defect_project_and_requirement, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="defect",
            name="project",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="defects", to="projects.project"),
        ),
    ]
