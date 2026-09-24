from django.conf import settings
from django.db import migrations, models
class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL),("test_cases","0001_initial")]
    operations=[migrations.CreateModel(name="Defect",fields=[("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("title",models.CharField(db_index=True,max_length=220)),("description",models.TextField()),("status",models.CharField(choices=[("OPEN","Open"),("IN_PROGRESS","In Progress"),("RESOLVED","Resolved"),("CLOSED","Closed")],db_index=True,default="OPEN",max_length=12)),("created_at",models.DateTimeField(auto_now_add=True)),("reported_by",models.ForeignKey(on_delete=models.deletion.PROTECT,related_name="reported_defects",to=settings.AUTH_USER_MODEL)),("test_case",models.ForeignKey(on_delete=models.deletion.CASCADE,related_name="defects",to="test_cases.testcase"))],options={"ordering":["-created_at"]})]
