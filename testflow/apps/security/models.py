from django.db import models
from django.utils import timezone
from apps.accounts.models import User

class SecurityEvent(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='actions')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    ip = models.GenericIPAddressField()
    event_type = models.CharField(max_length=40, db_index=True)
    success = models.BooleanField(db_index=True)
    reason = models.CharField(max_length=80, blank=True)
    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['user', 'created_at']), models.Index(fields=['ip', 'created_at'])]

class OneTimeToken(models.Model):
    class Kind(models.TextChoices):
        VERIFY = 'VERIFY'
        RESET = 'RESET'
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    kind = models.CharField(max_length=6, choices=Kind.choices)
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(default=timezone.now)
    class Meta:
        indexes = [models.Index(fields=['user', 'kind', 'consumed_at'])]

class TwoFactorSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    secret_encrypted = models.TextField(blank=True)
    pending_secret_encrypted = models.TextField(blank=True)
    pending_expires_at = models.DateTimeField(null=True)
    enabled = models.BooleanField(default=False)
    last_step = models.BigIntegerField(default=-1)

class RecoveryCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    used_at = models.DateTimeField(null=True)

class ExternalIdentity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='external_identities')
    provider = models.CharField(max_length=20, default='google')
    subject = models.CharField(max_length=255)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['provider', 'subject'], name='external_subject_unique')]

class AttemptBucket(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    key = models.CharField(max_length=64, unique=True)
    count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
    blocked_until = models.DateTimeField(null=True, db_index=True)
