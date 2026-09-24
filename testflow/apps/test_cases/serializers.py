from rest_framework import serializers
from apps.accounts.models import User
from .models import TestCase, TestStep


class TestStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestStep
        fields = ("id", "step_number", "action", "expected_result")
        read_only_fields = ("id",)


class TestCaseSerializer(serializers.ModelSerializer):
    steps = TestStepSerializer(many=True)
    project_name = serializers.CharField(source="project.name", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() or obj.assigned_to.username if obj.assigned_to else None
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username
    def validate_assigned_to(self, user):
        if user and user.role != User.Role.TESTER:
            raise serializers.ValidationError("A test case can be assigned only to a tester.")
        return user
    def validate_steps(self, steps):
        if not steps:
            raise serializers.ValidationError("Add at least one test step.")
        return steps
    def create(self, validated_data):
        steps = validated_data.pop("steps")
        test_case = TestCase.objects.create(**validated_data)
        TestStep.objects.bulk_create([
            TestStep(test_case=test_case, step_number=i + 1, action=step["action"], expected_result=step["expected_result"])
            for i, step in enumerate(steps)
        ])
        return test_case
    def update(self, instance, validated_data):
        steps = validated_data.pop("steps", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if steps is not None:
            instance.steps.all().delete()
            TestStep.objects.bulk_create([
                TestStep(test_case=instance, step_number=i + 1, action=step["action"], expected_result=step["expected_result"])
                for i, step in enumerate(steps)
            ])
        return instance
