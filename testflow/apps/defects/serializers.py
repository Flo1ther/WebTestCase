from rest_framework import serializers
from .models import Defect


class DefectSerializer(serializers.ModelSerializer):
    test_case_title = serializers.CharField(source="test_case.title", read_only=True)
    reported_by_name = serializers.SerializerMethodField()
    class Meta:
        model = Defect
        fields = "__all__"
        read_only_fields = ("reported_by", "created_at")
    def get_reported_by_name(self, obj):
        return obj.reported_by.get_full_name() or obj.reported_by.username
