from rest_framework import serializers

from apps.test_cases.models import TestCase
from apps.requirements.models import Requirement
from .models import AIAnalysis, AIFixProposal


class AnalyzeTestCaseSerializer(serializers.Serializer):
    test_case_id = serializers.PrimaryKeyRelatedField(queryset=TestCase.objects.all(), source="test_case")


class AnalyzeTextSerializer(serializers.Serializer):
    scenario = serializers.CharField(min_length=10, max_length=8000)


class GenerateTestCasesSerializer(serializers.Serializer):
    project_id = serializers.IntegerField(required=False, min_value=1)
    requirement_id = serializers.PrimaryKeyRelatedField(queryset=Requirement.objects.all(), required=False, allow_null=True, source="requirement")
    feature_description = serializers.CharField(min_length=10, max_length=4000)
    count = serializers.IntegerField(default=3, min_value=1, max_value=8)
    test_type = serializers.ChoiceField(choices=["POSITIVE", "NEGATIVE", "BOUNDARY", "MIXED"], default="MIXED")
    priority = serializers.ChoiceField(choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"], default="MEDIUM")
    detail_level = serializers.ChoiceField(choices=["COMPACT", "STANDARD", "DETAILED"], default="STANDARD")
    suite_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    api_test_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class CoverageSerializer(serializers.Serializer):
    requirement_id = serializers.PrimaryKeyRelatedField(queryset=Requirement.objects.all(), source="requirement")


class FixRequestSerializer(serializers.Serializer):
    finding_id = serializers.CharField(max_length=80)
    after = serializers.CharField(max_length=8000, required=False, allow_blank=False)


class AIFixProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIFixProposal
        fields = "__all__"
        read_only_fields = ("analysis", "finding_id", "target_field", "before", "rationale", "related_fields", "test_case_updated_at", "status", "decided_by", "created_at", "decided_at")


class AIAnalysisSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()
    test_case_title = serializers.CharField(source="test_case.title", read_only=True)
    fixes = AIFixProposalSerializer(many=True, read_only=True)

    class Meta:
        model = AIAnalysis
        fields = ("id", "project", "test_case", "test_case_title", "requirement", "requested_by", "requested_by_name", "analysis_type", "provider", "model_name", "result", "fixes", "created_at")

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.username
