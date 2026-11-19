from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("executions", "0007_apitest_requirement_testexecution_project"),
        ("projects", "0002_project_ai_context_project_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="GitHubIntegration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("repository_full_name", models.CharField(help_text="owner/repository", max_length=240, unique=True)),
                ("repository_url", models.URLField(blank=True)),
                ("default_branch", models.CharField(default="main", max_length=120)),
                ("workflow_file", models.CharField(blank=True, help_text=".github/workflows/qa.yml", max_length=240)),
                ("is_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="github_integration", to="projects.project")),
            ],
            options={"verbose_name": "GitHub integration", "verbose_name_plural": "GitHub integrations"},
        ),
        migrations.CreateModel(
            name="GitHubWorkflowRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider_run_id", models.CharField(max_length=160, unique=True)),
                ("source", models.CharField(choices=[("GITHUB_ACTIONS", "GitHub Actions"), ("LOCAL_SIMULATION", "Local simulation")], default="GITHUB_ACTIONS", max_length=20)),
                ("workflow_name", models.CharField(blank=True, max_length=240)),
                ("branch", models.CharField(blank=True, max_length=240)),
                ("commit_sha", models.CharField(blank=True, max_length=64)),
                ("commit_message", models.CharField(blank=True, max_length=500)),
                ("run_url", models.URLField(blank=True)),
                ("status", models.CharField(choices=[("QUEUED", "Queued"), ("IN_PROGRESS", "In progress"), ("COMPLETED", "Completed")], default="QUEUED", max_length=20)),
                ("conclusion", models.CharField(choices=[("SUCCESS", "Success"), ("FAILURE", "Failure"), ("CANCELLED", "Cancelled"), ("SKIPPED", "Skipped"), ("TIMED_OUT", "Timed out"), ("NEUTRAL", "Neutral"), ("UNKNOWN", "Unknown")], default="UNKNOWN", max_length=20)),
                ("received_payload", models.JSONField(blank=True, default=dict)),
                ("unmatched_automation_keys", models.JSONField(blank=True, default=list)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("integration", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workflow_runs", to="projects.githubintegration")),
                ("test_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="github_workflow_runs", to="executions.testrun")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="githubworkflowrun", index=models.Index(fields=["integration", "status"], name="projects_gi_integr_7fa946_idx")),
    ]
