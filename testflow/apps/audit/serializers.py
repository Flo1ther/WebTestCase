from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ("id", "user", "user_name", "action", "entity_type", "entity_id", "metadata", "created_at")

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username if obj.user else "System"
