from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies=[("ai_assistant","0005_aifixproposal")]
    operations=[migrations.CreateModel(name="AIBenchmarkRun",fields=[
        ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
        ("provider",models.CharField(max_length=40)),("model_name",models.CharField(max_length=120)),("dataset_version",models.CharField(default="qa-copilot-v1",max_length=40)),
        ("metrics",models.JSONField(default=dict)),("details",models.JSONField(default=list)),("created_at",models.DateTimeField(auto_now_add=True)),
        ("requested_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,to=settings.AUTH_USER_MODEL)),
    ],options={"ordering":["-created_at"]})]
