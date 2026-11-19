from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User


from apps.security.serializers import UserSerializer as SecurityUserSerializer

class UserSerializer(SecurityUserSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "full_name", "role", "is_active", "created_at", "email_verified", "manual_blocked", "two_factor_enabled", "providers", "has_password", "auto_blocked_until")
        read_only_fields = ("id", "created_at", "email_verified", "manual_blocked", "two_factor_enabled", "providers", "has_password", "auto_blocked_until")

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password")

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=User.Role.TESTER)


class AdminUserSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("password",)

    def validate_email(self, value):
        value = value.strip().lower()
        users = User.objects.filter(email__iexact=value)
        if self.instance: users = users.exclude(pk=self.instance.pk)
        if users.exists(): raise serializers.ValidationError('Ця електронна адреса вже використовується.')
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        user.set_password(password or ('Auto9!' + __import__("secrets").token_urlsafe(24)))
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.auth_version += 1
            instance.set_password(password)
        instance.save()
        return instance
