from rest_framework import serializers
from apps.test_cases.models import TestCase
from .models import TestExecution


class ExecutionSerializer(serializers.ModelSerializer):
    test_case_title = serializers.CharField(source="test_case.title", read_only=True)
    tester_name = serializers.SerializerMethodField()
    class Meta:
        model = TestExecution
        fields = "__all__"
        read_only_fields = ("tester", "executed_at")
    def get_tester_name(self, obj):
        return obj.tester.get_full_name() or obj.tester.username
    def validate(self, attrs):
        case = attrs["test_case"]
        user = self.context["request"].user
        if user.role == "TESTER" and case.assigned_to_id != user.id:
            raise serializers.ValidationError("This test case is not assigned to you.")
        return attrs
