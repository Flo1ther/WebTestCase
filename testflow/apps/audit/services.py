from typing import Any

from .models import AuditLog

SENSITIVE_KEYS = {"password", "token", "authorization", "secret", "api_key"}


def _safe(value: Any):
    if isinstance(value, dict):
        return {key: "[redacted]" if key.lower() in SENSITIVE_KEYS else _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return value


def record_action(*, user, action: str, entity_type: str, entity_id=None, metadata=None):
    """Store a compact, secret-free audit event without affecting the main request."""
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=_safe(metadata or {}),
    )
