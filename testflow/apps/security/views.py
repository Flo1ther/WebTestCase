import time
import secrets
from urllib.parse import urlparse, parse_qs
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, F
from django.db.models.functions import TruncDate
from django.http import HttpResponseRedirect
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, SecurityEvent, AttemptBucket, TwoFactorSettings, RecoveryCode
from .permissions import VerifiedUser, Administrator
from .serializers import RegistrationSerializer, UserSerializer, EventSerializer
from . import services as s
from .oidc import oauth

DUMMY_HASH = make_password('non-user-' + __import__('secrets').token_urlsafe(32))

@method_decorator(csrf_protect, name='dispatch')
class SecureView(APIView):
    # Account status and logout remain available before email activation;
    # application modules and sensitive account actions require VerifiedUser.
    permission_classes = [IsAuthenticated]

class PublicView(SecureView):
    permission_classes = [AllowAny]

def string(data, field, maximum=254, required=True):
    value = data.get(field, '')
    if not isinstance(value, str) or len(value) > maximum or (required and not value):
        raise ValidationError({field: 'Недійсне значення.'})
    return value

def new_password(data):
    password = string(data, 'password', 128)  # NOSONAR (S2068): validated request value, not a hard-coded credential.
    if password != string(data, 'password_confirm', 128): raise ValidationError({'password_confirm': 'Паролі не збігаються.'})  # NOSONAR (S2068): validated request fields, not credentials.
    validate_password(password)
    return password

def email_input(data):
    serializer = serializers.EmailField(max_length=254)
    return serializer.run_validation(data.get('email') or (User.objects.filter(username=data.get('username', '')).values_list('email', flat=True).first() if '@' not in data.get('username', '') else data.get('username')) or 'unknown@invalid.local').strip().lower()

def oidc_callback_uri(request):
    """Keep the OAuth callback on the same allowed browser origin as its session cookie."""
    origin = request.headers.get('Origin', '').rstrip('/')
    base = origin if origin in settings.CSRF_TRUSTED_ORIGINS else settings.PUBLIC_BASE_URL
    return base + '/api/auth/oidc/callback/'

class HealthView(PublicView):
    def get(self, request):
        User.objects.exists()
        return Response({'status': 'ok', 'database': 'postgresql'})

class ConfigView(PublicView):
    def get(self, request):
        redirect_uris = list(dict.fromkeys(origin + '/api/auth/oidc/callback/' for origin in settings.CSRF_TRUSTED_ORIGINS))
        return Response({'turnstile_site_key': settings.TURNSTILE_SITE_KEY, 'turnstile_test_mode': settings.TURNSTILE_TEST_MODE,
            'google_enabled': bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
            'email_verification_required': settings.EMAIL_VERIFICATION_REQUIRED,
            'google_redirect_uris': redirect_uris})

class CSRFView(PublicView):
    def get(self, request): return Response({'csrf_token': get_token(request)})

class RegisterView(PublicView):
    def post(self, request):
        s.rate_limit('register', s.ip_of(request), 10, 3600)
        data = RegistrationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        valid = data.validated_data
        s.verify_captcha(request, valid['captcha_token'])
        try:
            with transaction.atomic():
                user = User.objects.create_user(email=valid['email'], password=valid['password'], first_name=valid['first_name'], last_name=valid['last_name'], email_verified=not settings.EMAIL_VERIFICATION_REQUIRED)
                raw = s.issue_token(user, 'VERIFY') if settings.EMAIL_VERIFICATION_REQUIRED else None
                s.audit(request, 'REGISTER', True, user)
        except IntegrityError:
            raise ValidationError({'email': 'Реєстрацію неможливо завершити.'})
        if not settings.EMAIL_VERIFICATION_REQUIRED:
            return Response({'message': 'Акаунт створено та автоматично активовано для локальної демонстрації.', 'email_sent': False, 'email_verification_required': False}, status=201)
        sent = s.deliver(user, raw, 'VERIFY')
        return Response({'message': 'Акаунт створено. Підтвердьте email перед доступом до захищених функцій.', 'email_sent': sent, 'email_verification_required': True}, status=201)

class VerifyView(PublicView):
    def post(self, request):
        s.rate_limit('verify', s.ip_of(request), 30, 300)
        user = s.consume_token(string(request.data, 'token', 200), 'VERIFY')
        s.audit(request, 'EMAIL_VERIFIED', True, user)
        return Response({'message': 'Email підтверджено. Можна увійти.'})

class ResendView(PublicView):
    def post(self, request):
        email = email_input(request.data)
        s.rate_limit('email', s.ip_of(request), 10, 900)
        s.rate_limit('verify_resend', email, 3, 900)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=email, email_verified=False, manual_blocked=False).first()
            if user: raw = s.issue_token(user, 'VERIFY')
        if user: s.deliver(user, raw, 'VERIFY')
        return Response({'message': 'Якщо для цієї адреси потрібне підтвердження, лист надіслано.'})

class LoginView(PublicView):
    def post(self, request):
        email = email_input(request.data)
        password = string(request.data, 'password', 128)
        ip = s.ip_of(request)
        s.rate_limit('login_source', ip, 40, 900)
        try: s.check_lock(email, ip)
        except s.RateLimited:
            s.audit(request, 'LOGIN', False, User.objects.filter(email=email).first(), 'temporary_lock')
            raise
        user = User.objects.filter(email=email).first()
        valid = user.check_password(password) if user else check_password(password, DUMMY_HASH)
        if not valid or not user:
            state=s.login_failure(request, email, user)
            raise ValidationError({'detail': f"Email або пароль неправильні. Залишилося спроб: {state['attempts_remaining']}."})
        if user.manual_blocked or not user.is_active:
            s.audit(request, 'LOGIN', False, user, 'manual_block')
            raise PermissionDenied('Обліковий запис недоступний.')
        result = s.begin_login(request, user)
        if not result['requires_2fa']: AttemptBucket.objects.filter(key=s.login_key(email, ip)).update(count=0, blocked_until=None)
        return Response(result)

class OTPView(PublicView):
    def post(self, request):
        code = string(request.data, 'code', 128)
        s.rate_limit('otp_source', s.ip_of(request), 20, 300)
        pending = request.session.get('pending_auth')
        if not pending or pending['expires'] <= time.time():
            request.session.pop('pending_auth', None)
            raise ValidationError('Сеанс підтвердження прострочено. Увійдіть знову.')
        user = User.objects.filter(pk=pending['user_id'], auth_version=pending['version'], is_active=True, manual_blocked=False).first()
        if not user: raise PermissionDenied('Сеанс недоступний.')
        s.check_lock(user.email, s.ip_of(request))
        # Persistent per-user/source limit survives a fresh pre-auth session.
        s.rate_limit('otp_account', f'{user.pk}:{s.ip_of(request)}', settings.OTP_FAILURE_LIMIT, 300)
        if not s.verify_factor(user, code):
            s.audit(request, 'OTP', False, user, 'invalid_or_replayed')
            raise ValidationError({'code': 'Неправильний або вже використаний код.'})
        s.establish_session(request, user)
        AttemptBucket.objects.filter(key=s.login_key(user.email, s.ip_of(request))).update(count=0, blocked_until=None)
        s.audit(request, 'OTP', True, user)
        return Response({'message': 'Вхід підтверджено.'})

class LogoutView(SecureView):
    def post(self, request):
        s.audit(request, 'LOGOUT', True, request.user)
        logout(request)
        return Response({'message': 'Сеанс завершено.'})

class MeView(SecureView):
    def get(self, request): return Response(UserSerializer(request.user).data)
    def patch(self, request):
        if not request.user.email_verified: raise PermissionDenied('Підтвердьте email.')
        for field in ['first_name', 'last_name']:
            if field in request.data:
                value = string(request.data, field, 150).strip()
                if not value: raise ValidationError({field: 'Поле не може бути порожнім.'})
                setattr(request.user, field, value)
        request.user.save(update_fields=['first_name', 'last_name'])
        s.audit(request, 'PROFILE_UPDATED', True, request.user)
        return Response(UserSerializer(request.user).data)

class ProfileView(MeView):
    def get(self, request, pk):
        if pk != request.user.pk: raise PermissionDenied('Доступ лише до власного профілю.')
        return super().get(request)
    def patch(self, request, pk):
        if pk != request.user.pk: raise PermissionDenied('Доступ лише до власного профілю.')
        return super().patch(request)

class ForgotView(PublicView):
    def post(self, request):
        email = email_input(request.data)
        s.rate_limit('email', s.ip_of(request), 10, 900)
        s.rate_limit('reset_email', email, 3, 900)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=email, is_active=True, manual_blocked=False).first()
            if user: raw = s.issue_token(user, 'RESET')
        if user:
            s.deliver(user, raw, 'RESET')
            s.audit(request, 'RESET_REQUEST', True, user)
        return Response({'message': 'Якщо адреса зареєстрована, ви отримаєте лист для відновлення.'})

class ResetView(PublicView):
    def post(self, request):
        s.rate_limit('reset', s.ip_of(request), 15, 900)
        user = s.consume_token(string(request.data, 'token', 200), 'RESET', new_password(request.data))
        s.audit(request, 'PASSWORD_RESET', True, user)
        return Response({'message': 'Пароль змінено. Усі попередні сеанси припинено.'})

class ChangePasswordView(SecureView):
    permission_classes = [VerifiedUser]
    def post(self, request):
        s.reconfirm(request, string(request.data, 'current_password', 128, False))
        password = new_password(request.data)
        tf = TwoFactorSettings.objects.filter(user=request.user, enabled=True).exists()
        if tf and not s.verify_factor(request.user, string(request.data, 'code', 128)):
            raise ValidationError({'code': 'Підтвердьте другий фактор.'})
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            user.set_password(password)
            user.auth_version += 1
            user.save()
        s.audit(request, 'PASSWORD_CHANGED', True, user)
        logout(request)
        return Response({'message': 'Пароль змінено. Увійдіть знову.'})

class Setup2FAView(SecureView):
    permission_classes = [VerifiedUser]
    def post(self, request):
        s.reconfirm(request, string(request.data, 'password', 128, False))
        return Response(s.setup_factor(request.user))

class Enable2FAView(SecureView):
    permission_classes = [VerifiedUser]
    def post(self, request):
        s.rate_limit('enable_otp', str(request.user.pk), 5, 300)
        codes = s.enable_factor(request.user, string(request.data, 'code', 6))
        User.objects.filter(pk=request.user.pk).update(auth_version=F('auth_version') + 1)
        request.user.refresh_from_db()
        request.session['auth_version'] = request.user.auth_version
        s.audit(request, '2FA_ENABLED', True, request.user)
        return Response({'recovery_codes': codes, 'message': 'Збережіть резервні коди. Їх показано лише зараз.'})

class Disable2FAView(SecureView):
    permission_classes = [VerifiedUser]
    def post(self, request):
        s.reconfirm(request, string(request.data, 'password', 128, False))
        s.rate_limit('disable_otp', str(request.user.pk), 5, 300)
        if not s.verify_factor(request.user, string(request.data, 'code', 128)):
            raise ValidationError({'code': 'Потрібен чинний другий фактор або резервний код.'})
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            TwoFactorSettings.objects.filter(user=user).update(enabled=False, secret_encrypted='', pending_secret_encrypted='', last_step=-1)
            RecoveryCode.objects.filter(user=user).delete()
            user.auth_version += 1
            user.save(update_fields=['auth_version'])
        s.audit(request, '2FA_DISABLED', True, user)
        logout(request)
        return Response({'message': '2FA вимкнено. Увійдіть знову.'})

class GoogleStartView(PublicView):
    def post(self, request):
        s.rate_limit('oidc', s.ip_of(request), 15, 300)
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return Response({'message': 'Google OIDC ще не налаштовано. Додайте OAuth-ключі у .env.'}, status=503)
        mode = request.data.get('mode', 'login')
        if mode not in ['login', 'connect']: raise ValidationError('Недійсний режим.')
        connect = None
        if mode == 'connect':
            if not request.user.is_authenticated or not request.user.email_verified: raise PermissionDenied('Підтвердьте email і увійдіть.')
            s.reconfirm(request, string(request.data, 'password', 128, False))
            if TwoFactorSettings.objects.filter(user=request.user, enabled=True).exists() and not s.verify_factor(request.user, string(request.data, 'code', 128)):
                raise PermissionDenied('Підтвердьте другий фактор.')
            connect = {'user_id': request.user.pk, 'version': request.user.auth_version}
        redirect = oauth.google.authorize_redirect(request._request, oidc_callback_uri(request), prompt='select_account')
        state = parse_qs(urlparse(redirect['Location']).query)['state'][0]
        request.session['oidc_policy'] = {'state': state, 'connect': connect, 'expires': time.time() + 600}
        return Response({'url': redirect['Location']})

@require_http_methods(['GET'])
def google_callback(request):
    try:
        policy = request.session.pop('oidc_policy', None)
        if not policy or policy['expires'] < time.time() or not secrets.compare_digest(policy['state'], request.GET.get('state', '')):
            raise PermissionDenied('Недійсний OIDC state.')
        connect = policy['connect']
        token = oauth.google.authorize_access_token(request)
        user = s.resolve_google_identity(request, token['userinfo'], connect)
        if connect:
            return HttpResponseRedirect(settings.PUBLIC_BASE_URL + '/security?google=connected')
        s.check_lock(user.email, s.ip_of(request))
        result = s.begin_login(request, user)
        path = '/two-factor' if result['requires_2fa'] else '/profile'
        return HttpResponseRedirect(settings.PUBLIC_BASE_URL + path)
    except Exception:
        s.audit(request, 'OIDC', False, reason='provider_or_policy_rejection')
        return HttpResponseRedirect(settings.PUBLIC_BASE_URL + '/login?error=google')

class AdminUsersView(SecureView):
    permission_classes = [Administrator]
    def get(self, request):
        users = User.objects.all().select_related('two_factor').prefetch_related('external_identities')
        search = request.query_params.get('search', '')[:254]
        if search: users = users.filter(Q(email__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search))
        status = request.query_params.get('status')
        if status == 'verified': users = users.filter(email_verified=True, manual_blocked=False)
        if status == 'pending': users = users.filter(email_verified=False)
        if status == 'blocked': users = users.filter(Q(manual_blocked=True) | Q(attemptbucket__blocked_until__gt=timezone.now())).distinct()
        order = request.query_params.get('ordering', '-date_joined')
        if order not in ['email', '-email', 'date_joined', '-date_joined', 'last_name', '-last_name']: order = '-date_joined'
        users = users.order_by(order, 'id')
        paginator = PageNumberPagination()
        paginator.page_size = 12
        result = paginator.paginate_queryset(users, request)
        return paginator.get_paginated_response(UserSerializer(result, many=True).data)

class AdminUserView(SecureView):
    permission_classes = [Administrator]
    def get(self, request, pk):
        user = User.objects.filter(pk=pk).first()
        if not user: raise NotFound()
        return Response(UserSerializer(user).data)
    def post(self, request, pk):
        payload = serializers.BooleanField().run_validation(request.data.get('blocked'))
        with transaction.atomic():
            user = User.objects.select_for_update().filter(pk=pk).first()
            if not user: raise NotFound()
            if user.pk == request.user.pk: raise ValidationError('Не можна блокувати власний акаунт.')
            user.manual_blocked = payload
            user.is_active = not payload
            user.auth_version += 1
            user.save(update_fields=['manual_blocked', 'is_active', 'auth_version'])
            if not payload: AttemptBucket.objects.filter(user=user).update(count=0, blocked_until=None)
            s.audit(request, 'MANUAL_BLOCK' if payload else 'UNBLOCK', True, user, actor=request.user)
        return Response(UserSerializer(user).data)

class AdminEventsView(SecureView):
    permission_classes = [Administrator]
    def get(self, request):
        events = SecurityEvent.objects.select_related('user', 'actor').all()
        for param, lookup in [('email', 'user__email__icontains'), ('ip', 'ip'), ('type', 'event_type')]:
            value = request.query_params.get(param, '')
            if value:
                if param == 'ip':
                    try: __import__('ipaddress').ip_address(value)
                    except ValueError: raise ValidationError({'ip': 'Недійсна IP-адреса.'})
                events = events.filter(**{lookup: value[:254]})
        success = request.query_params.get('success', '')
        if success in ['true', 'false']: events = events.filter(success=success == 'true')
        for param, lookup in [('from', 'created_at__date__gte'), ('to', 'created_at__date__lte')]:
            value = request.query_params.get(param)
            if value:
                try: parsed = parse_date(value)
                except ValueError: parsed = None
                if not parsed: raise ValidationError({param: 'Дата має формат YYYY-MM-DD.'})
                events = events.filter(**{lookup: parsed})
        paginator = PageNumberPagination()
        paginator.page_size = 12
        result = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(EventSerializer(result, many=True).data)

class DashboardView(SecureView):
    permission_classes = [Administrator]
    def get(self, request):
        now = timezone.now()
        local_tz = timezone.get_current_timezone()
        start = timezone.localdate(now) - timedelta(days=29)
        window_start = now - timedelta(days=30)
        users = User.objects.all()
        blocked = users.filter(Q(manual_blocked=True) | Q(attemptbucket__blocked_until__gt=now)).distinct().count()
        counts = {'users': users.count(), 'verified': users.filter(email_verified=True).count(),
            'pending': users.filter(email_verified=False).count(), 'blocked': blocked,
            'failed_logins': SecurityEvent.objects.filter(event_type='LOGIN', success=False).count(),
            'two_factor': TwoFactorSettings.objects.filter(enabled=True).count()}
        # Filter by an aware timestamp, then group in the configured local timezone.
        # A date-only UTC filter can hide a just-created Kyiv account after midnight.
        registrations = {str(row['day']): row['count'] for row in users.filter(date_joined__gte=window_start).annotate(day=TruncDate('date_joined', tzinfo=local_tz)).values('day').annotate(count=Count('id'))}
        raw = SecurityEvent.objects.filter(created_at__gte=window_start, event_type__in=['LOGIN', 'AUTO_BLOCK']).annotate(day=TruncDate('created_at', tzinfo=local_tz)).values('day', 'event_type', 'success').annotate(count=Count('id'))
        events = {(str(row['day']), row['event_type'], row['success']): row['count'] for row in raw}
        timeline = []
        for offset in range(30):
            day = str(start + timedelta(days=offset))
            timeline.append({'date': day, 'registrations': registrations.get(day, 0), 'success': events.get((day, 'LOGIN', True), 0),
                'failed': events.get((day, 'LOGIN', False), 0), 'auto_blocks': events.get((day, 'AUTO_BLOCK', False), 0)})
        return Response({'counts': counts, 'timeline': timeline, 'statuses': [
            {'name': 'Активовані', 'value': users.filter(email_verified=True, manual_blocked=False).count()},
            {'name': 'Очікують', 'value': users.filter(email_verified=False, manual_blocked=False).count()},
            {'name': 'Заблоковані вручну', 'value': users.filter(manual_blocked=True).count()},
        ]})
