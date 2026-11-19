from rest_framework import serializers
from .models import Defect


class DefectSerializer(serializers.ModelSerializer):
    test_case_title = serializers.CharField(source="test_case.title", read_only=True)
    reported_by_name = serializers.SerializerMethodField()
    class Meta:
        model = Defect
        fields = "__all__"
        read_only_fields = ("project", "reported_by", "created_at")
    def get_reported_by_name(self, obj):
        return obj.reported_by.get_full_name() or obj.reported_by.username
    def validate(self, attrs):
        run = attrs.get("test_run")
        case = attrs.get("test_case", getattr(self.instance, "test_case", None))
        if run and case and run.project_id != case.project_id:
            raise serializers.ValidationError("Test Run дефекту має належати проєкту тесткейсу.")
        requirement = attrs.get("requirement", getattr(self.instance, "requirement", None))
        if requirement and case and requirement.project_id != case.project_id:
            raise serializers.ValidationError("Вимога дефекту має належати проєкту тесткейсу.")
        return attrs
