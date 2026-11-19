from rest_framework import serializers


class AnalyticsFilterSerializer(serializers.Serializer):
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    project_id = serializers.IntegerField(required=False, min_value=1)
    tester_id = serializers.IntegerField(required=False, min_value=1)
    status = serializers.ChoiceField(required=False, choices=["PASSED", "FAILED", "BLOCKED", "NOT_RUN"])

    def validate(self, attrs):
        if attrs.get("date_from") and attrs.get("date_to") and attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError("date_from must be before date_to.")
        return attrs
