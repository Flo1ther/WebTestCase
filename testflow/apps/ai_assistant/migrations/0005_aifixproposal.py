from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("ai_assistant", "0004_aianalysis_requirement")]
    operations = [
        migrations.AlterField(model_name="aianalysis", name="analysis_type", field=models.CharField(choices=[("ANALYZE", "Analyze test case"), ("GENERATE", "Підготувати пропозиції"), ("COVERAGE", "Coverage analysis"), ("API", "API assistant")], max_length=16)),
        migrations.CreateModel(name="AIFixProposal", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("finding_id", models.CharField(max_length=80)), ("target_field", models.CharField(max_length=80)),
            ("before", models.TextField()), ("after", models.TextField()), ("rationale", models.TextField()),
            ("related_fields", models.JSONField(blank=True, default=list)), ("test_case_updated_at", models.DateTimeField()),
            ("status", models.CharField(choices=[("PROPOSED", "Proposed"), ("APPLIED", "Applied"), ("REJECTED", "Rejected")], default="PROPOSED", max_length=12)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("decided_at", models.DateTimeField(blank=True, null=True)),
            ("analysis", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fixes", to="ai_assistant.aianalysis")),
            ("decided_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ai_fix_decisions", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering":["-created_at"]}),
        migrations.AddConstraint(model_name="aifixproposal", constraint=models.UniqueConstraint(fields=("analysis", "finding_id"), name="unique_ai_fix_per_finding")),
    ]
