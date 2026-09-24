from rest_framework import serializers
from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)
    test_case_count = serializers.IntegerField(read_only=True)
    progress = serializers.FloatField(read_only=True)

    class Meta:
        model = Project
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")
