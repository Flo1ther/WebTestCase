"""Security operations: database locks protect single-use credentials and counters."""
import hashlib
import hmac
import io
import ipaddress
import secrets
import time
from datetime import timedelta
from base64 import b64encode
import pyotp
import qrcode
import qrcode.image.svg
import requests
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied
from .models import User, OneTimeToken, SecurityEvent, AttemptBucket, TwoFactorSettings, RecoveryCode, ExternalIdentity

class RateLimited(APIException):
    status_code = 429
    default_detail = 'Забагато спроб. Спробуйте пізніше.'
    default_code = 'rate_limited'

def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def key(value): return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()
def ip_of(request):
    try:
        ip = ipaddress.ip_address(request.META.get('REMOTE_ADDR', '127.0.0.1'))
        trusted = [ipaddress.ip_network(v) for v in settings.TRUSTED_PROXY_IPS]
        if any(ip in network for network in trusted):
            chain = [ipaddress.ip_address(v.strip()) for v in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if v.strip()]
            for candidate in reversed(chain):
                ip = candidate
                if not any(candidate in network for network in trusted): break
        return str(ip)
    except ValueError:
        return '127.0.0.1'

def audit(request, event_type, success=True, user=None, reason='', actor=None):
    return SecurityEvent.objects.create(user=user, actor=actor, ip=ip_of(request), event_type=event_type, success=success, reason=reason)

@transaction.atomic
def rate_limit(scope, identity, limit, seconds):
    bucket, _ = AttemptBucket.objects.get_or_create(key=key(scope + ':' + identity))
    bucket = AttemptBucket.objects.select_for_update().get(pk=bucket.pk)
    now = timezone.now()
    if bucket.started_at + timedelta(seconds=seconds) <= now:
        bucket.started_at, bucket.count = now, 0
    if bucket.count >= limit:
        raise RateLimited()
    bucket.count += 1
    bucket.save(update_fields=['count', 'started_at'])

def login_key(email, ip): return key('login:' + email.lower() + ':' + ip)
def check_lock(email, ip):
    bucket = AttemptBucket.objects.filter(key=login_key(email, ip)).first()
    if bucket and bucket.blocked_until and bucket.blocked_until > timezone.now():
        raise RateLimited('Цей вхід тимчасово заблоковано на 15 хвилин.')

@transaction.atomic
def login_failure(request, email, user=None, reason='invalid_credentials'):
    now = timezone.now()
    bucket, _ = AttemptBucket.objects.get_or_create(key=login_key(email, ip_of(request)))
    bucket = AttemptBucket.objects.select_for_update().get(pk=bucket.pk)
    if bucket.started_at + timedelta(seconds=settings.LOGIN_LOCK_SECONDS) <= now:
        bucket.started_at, bucket.count, bucket.blocked_until = now, 0, None
    bucket.count += 1
    bucket.user = user
    if bucket.count == settings.LOGIN_FAILURE_LIMIT:
        bucket.blocked_until = now + timedelta(seconds=settings.LOGIN_LOCK_SECONDS)
        audit(request, 'AUTO_BLOCK', False, user, 'login_limit')
    bucket.save()
    audit(request, 'LOGIN', False, user, reason)
    return {'attempts_remaining': max(0, settings.LOGIN_FAILURE_LIMIT - bucket.count), 'blocked': bool(bucket.blocked_until and bucket.blocked_until > now)}

def verify_captcha(request, token):
    if not token or not isinstance(token, str) or len(token) > 2048:
        raise ValidationError({'captcha_token': 'Пройдіть перевірку CAPTCHA.'})
    try:
        result = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={'secret': settings.TURNSTILE_SECRET_KEY, 'response': token, 'remoteip': ip_of(request)}, timeout=10).json()
    except (requests.RequestException, ValueError):
        raise ValidationError({'captcha_token': 'Перевірка CAPTCHA тимчасово недоступна.'})
    if not result.get('success'):
        raise ValidationError({'captcha_token': 'CAPTCHA недійсна або прострочена. Повторіть перевірку.'})
    if not settings.TURNSTILE_TEST_MODE:
        if result.get('hostname') not in settings.TURNSTILE_ALLOWED_HOSTNAMES or result.get('action') != 'register':
            raise ValidationError({'captcha_token': 'Недійсне джерело CAPTCHA.'})

def issue_token(user, kind):
    raw = secrets.token_urlsafe(32)
    OneTimeToken.objects.filter(user=user, kind=kind, consumed_at=None).update(consumed_at=timezone.now())
    OneTimeToken.objects.create(user=user, kind=kind, digest=digest(raw),
        expires_at=timezone.now() + timedelta(hours=24) if kind == 'VERIFY' else timezone.now() + timedelta(minutes=30))
    return raw

def deliver(user, raw, kind):
    path = '/verify-email' if kind == 'VERIFY' else '/reset-password'
    subject = 'Підтвердження email' if kind == 'VERIFY' else 'Відновлення пароля'
    lifetime = '24 години' if kind == 'VERIFY' else '30 хвилин'
    url = f'{settings.PUBLIC_BASE_URL}{path}?token={raw}'
    try:
        send_mail(subject, f'{subject}\n\n{url}\n\nПосилання діє {lifetime} та використовується лише один раз.\nЯкщо ви не надсилали запит, ігноруйте лист.', settings.DEFAULT_FROM_EMAIL, [user.email])
        return True
    except Exception:
        # Do not log SMTP data or bearer links; the authenticated user can resend.
        return False

@transaction.atomic
def consume_token(raw, kind, new_password=None):
    if not raw or len(raw) > 200: raise ValidationError('Посилання недійсне або прострочене.')
    candidate = OneTimeToken.objects.filter(digest=digest(raw), kind=kind).values('id', 'user_id').first()
    if not candidate: raise ValidationError('Посилання недійсне або прострочене.')
    # Consistent user-before-token ordering also matches resend/reset issuance.
    user = User.objects.select_for_update().get(pk=candidate['user_id'])
    token = OneTimeToken.objects.select_for_update().filter(pk=candidate['id']).first()
    if not token or token.consumed_at or token.expires_at <= timezone.now():
        raise ValidationError('Посилання недійсне, прострочене або вже використане.')
    if kind == 'VERIFY':
        user.email_verified = True
    else:
        validate_password(new_password, user)
        user.set_password(new_password)
        user.auth_version += 1
    user.save()
    token.consumed_at = timezone.now()
    token.save(update_fields=['consumed_at'])
    if kind == 'RESET':
        OneTimeToken.objects.filter(user=user, kind='RESET', consumed_at=None).update(consumed_at=timezone.now())
    return user

def cipher(): return Fernet(settings.TOTP_ENCRYPTION_KEY.encode())
def encrypt(secret): return cipher().encrypt(secret.encode()).decode()
def decrypt(secret): return cipher().decrypt(secret.encode()).decode()

def totp_step(secret, code, last_step=-1):
    if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdecimal(): return None
    current = int(time.time() // 30)
    totp = pyotp.TOTP(secret)
    for step in (current, current-1, current+1):
        if step > last_step and hmac.compare_digest(totp.at(step * 30), code): return step
    return None

@transaction.atomic
def verify_factor(user, code):
    tf = TwoFactorSettings.objects.select_for_update().filter(user=user, enabled=True).first()
    if not tf: return False
    step = totp_step(decrypt(tf.secret_encrypted), code, tf.last_step)
    if step is not None:
        tf.last_step = step
        tf.save(update_fields=['last_step'])
        return True
    recovery = RecoveryCode.objects.select_for_update().filter(user=user, digest=key('recovery:' + code), used_at=None).first()
    if recovery:
        recovery.used_at = timezone.now()
        recovery.save(update_fields=['used_at'])
        return True
    return False

def reconfirm(request, password='', code=''):
    user = request.user
    rate_limit('reconfirm', f'{user.pk}:{ip_of(request)}', 10, 300)
    if user.has_usable_password():
        if not password or not user.check_password(password): raise PermissionDenied('Підтвердьте поточний пароль.')
    else:
        if request.session.get('reauth_at', 0) + 300 < time.time():
            raise PermissionDenied('Повторно увійдіть через Google для підтвердження особи.')
    request.session['reauth_at'] = time.time()

def establish_session(request, user):
    if user.manual_blocked or not user.is_active: raise PermissionDenied('Обліковий запис недоступний.')
    request.session.pop('pending_auth', None)
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    request.session['auth_version'] = user.auth_version
    request.session['reauth_at'] = time.time()
    audit(request, 'LOGIN', True, user)

def begin_login(request, user):
    if user.manual_blocked or not user.is_active: raise PermissionDenied('Обліковий запис недоступний.')
    if TwoFactorSettings.objects.filter(user=user, enabled=True).exists():
        if request.user.is_authenticated:
            logout(request)
        request.session.cycle_key()
        request.session['pending_auth'] = {'user_id': user.pk, 'version': user.auth_version,
            'expires': time.time() + settings.CHALLENGE_SECONDS, 'id': secrets.token_hex(16), 'attempts': 0}
        return {'requires_2fa': True}
    establish_session(request, user)
    return {'requires_2fa': False}

@transaction.atomic
def setup_factor(user):
    tf, _ = TwoFactorSettings.objects.get_or_create(user=user)
    tf = TwoFactorSettings.objects.select_for_update().get(pk=tf.pk)
    if tf.enabled: raise ValidationError('2FA вже увімкнено.')
    secret = pyotp.random_base32()
    tf.pending_secret_encrypted = encrypt(secret)
    tf.pending_expires_at = timezone.now() + timedelta(minutes=10)
    tf.save()
    uri = pyotp.TOTP(secret).provisioning_uri(user.email, issuer_name='WebTestCase')
    svg = io.BytesIO()
    qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).save(svg)
    return {'secret': secret, 'qr_code': 'data:image/svg+xml;base64,' + b64encode(svg.getvalue()).decode()}

@transaction.atomic
def enable_factor(user, code):
    tf = TwoFactorSettings.objects.select_for_update().filter(user=user).first()
    if not tf or not tf.pending_secret_encrypted or not tf.pending_expires_at or tf.pending_expires_at <= timezone.now():
        raise ValidationError('Налаштування прострочено. Створіть новий QR-код.')
    if tf.enabled: raise ValidationError('2FA вже увімкнено.')
    step = totp_step(decrypt(tf.pending_secret_encrypted), code)
    if step is None: raise ValidationError({'code': 'Неправильний код.'})
    tf.secret_encrypted, tf.pending_secret_encrypted = tf.pending_secret_encrypted, ''
    tf.enabled, tf.last_step, tf.pending_expires_at = True, step, None
    tf.save()
    RecoveryCode.objects.filter(user=user).delete()
    codes = [secrets.token_hex(5).upper() for _ in range(10)]
    RecoveryCode.objects.bulk_create([RecoveryCode(user=user, digest=key('recovery:' + code)) for code in codes])
    return codes

@transaction.atomic
def resolve_google_identity(request, claims, connect=None):
    # Authlib verified signature, nonce, issuer, audience and expiry before this boundary.
    if claims.get('email_verified') is not True or not claims.get('sub') or not claims.get('email'):
        raise PermissionDenied('Google не підтвердив email.')
    email = claims['email'].strip().lower()
    identity = ExternalIdentity.objects.select_for_update().select_related('user').filter(provider='google', subject=claims['sub']).first()
    if connect:
        user = User.objects.select_for_update().get(pk=connect['user_id'])
        if user.auth_version != connect['version'] or user.manual_blocked or not user.email_verified:
            raise PermissionDenied('Прив’язування недоступне.')
        if identity and identity.user_id != user.pk: raise PermissionDenied('Google-акаунт уже прив’язано.')
        if not identity: ExternalIdentity.objects.create(user=user, provider='google', subject=claims['sub'])
        audit(request, 'OIDC_LINK', True, user)
        return user
    if identity: return identity.user
    if User.objects.filter(email__iexact=email).exists():
        raise PermissionDenied('Увійдіть до наявного профілю та прив’яжіть Google у налаштуваннях безпеки.')
    user = User.objects.create_user(email=email, first_name=str(claims.get('given_name', ''))[:150],
        last_name=str(claims.get('family_name', ''))[:150], email_verified=True)
    ExternalIdentity.objects.create(user=user, provider='google', subject=claims['sub'])
    audit(request, 'REGISTER_OIDC', True, user)
    return user
