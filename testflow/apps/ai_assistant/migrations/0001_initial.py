# Generated manually for the TestFlow educational project.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("test_cases", "0001_initial")]
    operations = [
        migrations.CreateModel(
            name="AIAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("analysis_type", models.CharField(choices=[("ANALYZE", "Analyze test case"), ("GENERATE", "Generate suggestions")], max_length=16)),
                ("provider", models.CharField(max_length=40)), ("model_name", models.CharField(max_length=120)),
                ("result", models.JSONField(default=dict)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ai_analyses", to=settings.AUTH_USER_MODEL)),
                ("test_case", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_analyses", to="test_cases.testcase")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="aianalysis", index=models.Index(fields=["requested_by", "created_at"], name="ai_assistan_request_7177cf_idx")),
        migrations.AddIndex(model_name="aianalysis", index=models.Index(fields=["test_case", "created_at"], name="ai_assistan_test_ca_817921_idx")),
    ]
