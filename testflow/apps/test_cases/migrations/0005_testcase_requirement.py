import django.db.models.deletion
from django.db import migrations, models


def copy_existing_requirement(apps, schema_editor):
    TestCase = apps.get_model("test_cases", "TestCase")
    for case in TestCase.objects.all().iterator():
        requirement = case.requirements.order_by("id").first()
        if requirement:
            case.requirement_id = requirement.id
            case.save(update_fields=["requirement"])


class Migration(migrations.Migration):
    dependencies = [("requirements", "0001_initial"), ("test_cases", "0004_testsuite")]

    operations = [
        migrations.AddField(
            model_name="testcase",
            name="requirement",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="primary_test_cases", to="requirements.requirement"),
        ),
        migrations.RunPython(copy_existing_requirement, migrations.RunPython.noop),
    ]
