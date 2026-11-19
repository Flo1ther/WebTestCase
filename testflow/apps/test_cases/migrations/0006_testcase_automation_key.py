from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("test_cases", "0005_testcase_requirement")]

    operations = [
        migrations.AddField(
            model_name="testcase",
            name="automation_key",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
    ]
