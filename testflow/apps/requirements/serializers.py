from rest_framework import serializers
from apps.test_cases.models import TestCase
from .models import Requirement


class RequirementSerializer(serializers.ModelSerializer):
    test_case_ids = serializers.PrimaryKeyRelatedField(source="test_cases", many=True, queryset=TestCase.objects.all(), required=False)
    covered = serializers.SerializerMethodField()
    class Meta:
        model = Requirement
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")
    def validate(self, attrs):
        project = attrs.get("project", getattr(self.instance, "project", None))
        key = attrs.get("key", getattr(self.instance, "key", "")).strip()
        duplicate = Requirement.objects.filter(project=project, key__iexact=key)
        if self.instance:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if project and key and duplicate.exists():
            raise serializers.ValidationError({"key": f"У проєкті «{project.name}» уже є вимога з ключем «{key}». Вкажіть інший ключ."})
        cases = attrs.get("test_cases")
        if cases is not None and any(case.project_id != project.id for case in cases):
            raise serializers.ValidationError("Тесткейси вимоги повинні належати тому самому проєкту.")
        return attrs
    def get_covered(self, obj):
        return obj.test_cases.exists()
