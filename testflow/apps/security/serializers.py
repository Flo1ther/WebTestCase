from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import User, SecurityEvent
from django.utils import timezone

class RegistrationSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)  # NOSONAR (S2068): request field, not a hard-coded credential.
    password_confirm = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    captcha_token = serializers.CharField(max_length=2048, trim_whitespace=False, write_only=True)
    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists(): raise serializers.ValidationError('Реєстрацію з цим email неможливо завершити. Скористайтесь входом або відновленням.')
        return value
    def validate(self, data):
        if data['password'] != data['password_confirm']: raise serializers.ValidationError({'password_confirm': 'Паролі не збігаються.'})  # NOSONAR (S2068): validated request fields, not credentials.
        try: validate_password(data['password'])
        except DjangoValidationError as error: raise serializers.ValidationError({'password': error.messages})
        return data

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    def get_full_name(self, obj): return obj.get_full_name() or obj.username
    auto_blocked_until = serializers.SerializerMethodField()
    two_factor_enabled = serializers.SerializerMethodField()
    providers = serializers.SerializerMethodField()
    has_password = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['username', 'full_name', 'is_active', 'created_at', 'id', 'email', 'first_name', 'last_name', 'role', 'email_verified', 'manual_blocked', 'auto_blocked_until', 'date_joined', 'last_login', 'two_factor_enabled', 'providers', 'has_password']
    def get_auto_blocked_until(self, user):
        bucket = user.attemptbucket_set.filter(blocked_until__gt=timezone.now()).order_by('-blocked_until').first()
        return bucket.blocked_until if bucket else None
    def get_two_factor_enabled(self, user): return hasattr(user, 'two_factor') and user.two_factor.enabled
    def get_providers(self, user): return list(user.external_identities.values_list('provider', flat=True))
    def get_has_password(self, user): return user.has_usable_password()

class EventSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', default=None)
    actor_email = serializers.CharField(source='actor.email', default=None)
    class Meta:
        model = SecurityEvent
        fields = ['id', 'user_id', 'user_email', 'actor_email', 'created_at', 'ip', 'event_type', 'success', 'reason']
