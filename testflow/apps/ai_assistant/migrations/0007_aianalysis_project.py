from django.db import migrations, models
import django.db.models.deletion


def populate_analysis_project(apps, schema_editor):
    AIAnalysis = apps.get_model("ai_assistant", "AIAnalysis")
    for analysis in AIAnalysis.objects.select_related("test_case", "requirement").all().iterator():
        if analysis.test_case_id:
            analysis.project_id = analysis.test_case.project_id
        elif analysis.requirement_id:
            analysis.project_id = analysis.requirement.project_id
        if analysis.project_id:
            analysis.save(update_fields=["project"])


class Migration(migrations.Migration):
    dependencies = [
        ("ai_assistant", "0006_aibenchmarkrun"),
        ("projects", "0002_project_ai_context_project_status"),
    ]
    operations = [
        migrations.AddField(
            model_name="aianalysis",
            name="project",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_analyses", to="projects.project"),
        ),
        migrations.RunPython(populate_analysis_project, migrations.RunPython.noop),
    ]
