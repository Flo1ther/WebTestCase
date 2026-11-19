from rest_framework import serializers
from django.db import transaction
from apps.accounts.models import User
from .models import TestCase, TestStep, TestSuite


class TestSuiteSerializer(serializers.ModelSerializer):
    test_case_ids = serializers.PrimaryKeyRelatedField(source="test_cases", many=True, queryset=TestCase.objects.all(), required=False)
    class Meta:
        model = TestSuite
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")
    def validate(self, attrs):
        project=attrs.get("project",getattr(self.instance,"project",None)); cases=attrs.get("test_cases")
        if cases is not None and any(case.project_id != project.id for case in cases):
            raise serializers.ValidationError("Test Suite може містити лише тесткейси свого проєкту.")
        return attrs


class TestStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestStep
        fields = ("id", "step_number", "action", "expected_result")
        read_only_fields = ("id",)


class TestCaseSerializer(serializers.ModelSerializer):
    steps = TestStepSerializer(many=True)
    automation_key = serializers.CharField(required=False, allow_blank=True, max_length=120)
    project_name = serializers.CharField(source="project.name", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    requirement_key = serializers.CharField(source="requirement.key", read_only=True)

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
            raise serializers.ValidationError('Тесткейс можна призначити лише тестувальнику.')
        return user
    def validate_automation_key(self, value):
        # Normalising makes a key copied from a CI configuration reliable.
        return value.strip().upper()
    def validate_steps(self, steps):
        if not steps:
            raise serializers.ValidationError('Додайте принаймні один крок перевірки.')
        return steps
    def validate(self, attrs):
        project = attrs.get("project", getattr(self.instance, "project", None))
        requirement = attrs.get("requirement", getattr(self.instance, "requirement", None))
        automation_key = attrs.get("automation_key", getattr(self.instance, "automation_key", ""))
        if project and automation_key:
            duplicate = TestCase.objects.filter(project=project, automation_key__iexact=automation_key)
            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError({"automation_key": "У цьому проєкті вже є тесткейс з таким ключем автоматизації."})
        if requirement and project and requirement.project_id != project.id:
            raise serializers.ValidationError({"requirement": "Вимога тесткейсу повинна належати вибраному проєкту."})
        return attrs
    def create(self, validated_data):
        steps = validated_data.pop("steps")
        with transaction.atomic():
            test_case = TestCase.objects.create(**validated_data)
            TestStep.objects.bulk_create([
                TestStep(test_case=test_case, step_number=i + 1, action=step["action"], expected_result=step["expected_result"])
                for i, step in enumerate(steps)
            ])
        return test_case
    def update(self, instance, validated_data):
        steps = validated_data.pop("steps", None)
        with transaction.atomic():
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
