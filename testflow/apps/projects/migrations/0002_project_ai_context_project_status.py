from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="project",
            name="ai_context",
            field=models.TextField(blank=True, help_text="Domain, terminology, users, constraints and acceptance context for AI QA."),
        ),
        migrations.AddField(
            model_name="project",
            name="status",
            field=models.CharField(choices=[("ACTIVE", "Active"), ("ON_HOLD", "On hold"), ("ARCHIVED", "Archived")], db_index=True, default="ACTIVE", max_length=12),
        ),
    ]
