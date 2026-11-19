# Generated manually for the immutable execution snapshot.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("executions", "0005_apitest_apiexecution"),
    ]

    operations = [
        migrations.AddField(
            model_name="testexecution",
            name="test_case_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
