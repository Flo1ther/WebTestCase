from datetime import timedelta
from unittest.mock import patch, Mock
import time
import pytest
import pyotp
from django.test import Client, RequestFactory, override_settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from apps.security.models import User, OneTimeToken, SecurityEvent, AttemptBucket, TwoFactorSettings, RecoveryCode, ExternalIdentity
from apps.security import services as s

pytestmark = pytest.mark.django_db
PASSWORD = 'SafePass9!demo'

@pytest.fixture(autouse=True)
def mail_settings(settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    settings.ALLOWED_HOSTS += ['testserver']

@pytest.fixture
def user(): return User.objects.create_user(email='user@example.com', password=PASSWORD, first_name='Марія', last_name='Шевчук', email_verified=True)
@pytest.fixture
def admin(): return User.objects.create_superuser(email='admin@example.com', password=PASSWORD, first_name='Адмін', last_name='Системи')
@pytest.fixture
def client(): return Client()

def post(client, path, data): return client.post('/api/' + path + '/', data, content_type='application/json')
def signin(client, user):
    response = post(client, 'auth/login', {'email': user.email, 'password': PASSWORD})
    assert response.status_code == 200
    return response

def register(client, **changes):
    data = dict(email='new@example.com', first_name='Ірина', last_name='Шевчук', password=PASSWORD, password_confirm=PASSWORD, captcha_token='test-token')
    data.update(changes)
    with patch('apps.security.services.requests.post', return_value=Mock(json=lambda:{'success':True})):
        return post(client, 'auth/register', data)

def request():
    req = RequestFactory().get('/')
    SessionMiddleware(lambda r:None).process_request(req)
    req.user = AnonymousUser()
    return req

def test_registration_argon2_email_token(client):
    assert register(client).status_code == 201
    u = User.objects.get(email='new@example.com')
    assert not u.email_verified and u.password.startswith('argon2$argon2id$')
    assert u.check_password(PASSWORD) and len(mail.outbox) == 1
    raw = mail.outbox[0].body.split('token=')[1].split()[0]
    token = OneTimeToken.objects.get(user=u)
    assert raw != token.digest and token.digest == s.digest(raw)
    assert post(client, 'auth/verify-email', {'token':raw}).status_code == 200
    assert post(client, 'auth/verify-email', {'token':raw}).status_code == 400
    u.refresh_from_db(); assert u.email_verified

@pytest.mark.parametrize('password', ['short', 'alllower9!', 'ALLUPPER9!', 'NoDigitPass!', 'NoSpecial99', 'A9!'])
def test_password_policy(client, password):
    assert register(client, password=password, password_confirm=password).status_code == 400
    assert not User.objects.exists()

def test_password_confirmation(client): assert register(client,password_confirm='different').status_code == 400
def test_duplicate_case(client,user): assert register(client,email='USER@EXAMPLE.COM').status_code == 400
def test_database_duplicate_case(user):
    with pytest.raises(IntegrityError), transaction.atomic(): User.objects.create_user(email='USER@EXAMPLE.COM',password=PASSWORD)

def test_server_rejects_captcha(client):
    with patch('apps.security.services.requests.post',return_value=Mock(json=lambda:{'success':False})):
        r=post(client,'auth/register',dict(email='x@example.com',first_name='X',last_name='Y',password=PASSWORD,password_confirm=PASSWORD,captcha_token='invalid'))
    assert r.status_code == 400 and not User.objects.exists()

def test_production_captcha_hostname_action():
    with override_settings(TURNSTILE_TEST_MODE=False,TURNSTILE_ALLOWED_HOSTNAMES=['example.com']),patch('apps.security.services.requests.post',return_value=Mock(json=lambda:{'success':True,'hostname':'evil.com','action':'register'})):
        with pytest.raises(Exception): s.verify_captcha(request(),'token')

def test_csrf_required_for_anonymous_post():
    c=Client(enforce_csrf_checks=True)
    assert post(c,'auth/login',{'email':'x@example.com','password':PASSWORD}).status_code == 403
    c.get('/api/csrf/')
    r=c.post('/api/auth/forgot-password/',{'email':'x@example.com'},content_type='application/json',HTTP_X_CSRFTOKEN=c.cookies['csrftoken'].value)
    assert r.status_code == 200

def test_login_cookie_and_rbac(client,user):
    signin(client,user)
    assert client.cookies['sessionid']['httponly'] and client.cookies['sessionid']['samesite']=='Lax'
    assert client.get('/api/me/').status_code == 200
    assert client.get('/api/security/admin/users/').status_code == 403
    assert client.get('/api/security/admin/events/').status_code == 403
    assert client.get('/api/security/admin/dashboard/').status_code == 403

def test_pending_email_restricted(client,user):
    user.email_verified=False;user.save();signin(client,user)
    assert client.get('/api/me/').status_code == 200
    assert client.get('/api/me/').json()['email_verified'] is False
    assert client.patch('/api/me/',{'first_name':'Changed'},content_type='application/json').status_code == 403
    assert post(client,'security/2fa/setup',{'password':PASSWORD}).status_code == 403
    assert post(client,'auth/logout',{}).status_code == 200

def test_setup_2fa_endpoint_accepts_current_password(client, user):
    signin(client, user)
    response = post(client, 'security/2fa/setup', {'password': PASSWORD})
    assert response.status_code == 200
    assert response.json()['secret'] and response.json()['qr_code'].startswith('data:image/svg+xml;base64,')

def test_idor_and_role_escalation(client,user,admin):
    signin(client,user)
    assert client.get(f'/api/profiles/{admin.pk}/').status_code == 403
    assert client.patch(f'/api/profiles/{admin.pk}/',{'first_name':'attack'},content_type='application/json').status_code == 403
    assert client.patch('/api/me/',{'first_name':'Олена','role':'ADMIN','email_verified':True},content_type='application/json').status_code == 200
    user.refresh_from_db(); assert user.role=='TESTER' and user.first_name=='Олена'

def test_five_failures_lock_pair_and_audit(client,user):
    for _ in range(5): assert post(client,'auth/login',{'email':user.email,'password':'Wrong9!pass'}).status_code == 400
    assert post(client,'auth/login',{'email':user.email,'password':PASSWORD}).status_code == 429
    assert SecurityEvent.objects.filter(event_type='AUTO_BLOCK').count()==1
    assert client.post('/api/auth/login/',{'email':user.email,'password':PASSWORD},content_type='application/json',REMOTE_ADDR='127.0.0.2').status_code==200
    assert not SecurityEvent.objects.filter(reason__contains=PASSWORD).exists()

def test_lock_expiry(client,user):
    for _ in range(5): post(client,'auth/login',{'email':user.email,'password':'wrong'})
    AttemptBucket.objects.filter(user=user).update(blocked_until=timezone.now()-timedelta(seconds=1))
    assert signin(client,user).status_code==200

def test_manual_block_invalidation_and_unblock(user,admin):
    c=Client();signin(c,user);a=Client();signin(a,admin)
    assert post(a,f'security/admin/users/{user.pk}',{'blocked':True}).status_code==200
    assert c.get('/api/me/').status_code==403
    assert post(c,'auth/login',{'email':user.email,'password':PASSWORD}).status_code==403
    assert post(a,f'security/admin/users/{user.pk}',{'blocked':False}).status_code==200
    assert signin(c,user).status_code==200
    assert post(a,f'security/admin/users/{admin.pk}',{'blocked':True}).status_code==400

def test_admin_filter_pagination_dashboard(client,admin,user):
    signin(client,admin)
    assert client.get('/api/security/admin/users/?search=user@example').json()['count']==1
    dashboard=client.get('/api/security/admin/dashboard/').json()
    assert dashboard['counts']['users']==2 and len(dashboard['timeline'])==30
    assert sum(t['registrations'] for t in dashboard['timeline'])==2
    assert client.get('/api/security/admin/events/?type=LOGIN&success=true').json()['count']==1
    assert client.get('/api/security/admin/events/?ip=bad-ip').status_code==400
    assert client.get('/api/security/admin/events/?from=bad-date').status_code==400

def test_expired_tokens(user):
    token=s.issue_token(user,'RESET')
    OneTimeToken.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
    with pytest.raises(Exception):s.consume_token(token,'RESET',PASSWORD)

def test_resend_invalidates_previous(user):
    first=s.issue_token(user,'VERIFY');second=s.issue_token(user,'VERIFY')
    with pytest.raises(Exception):s.consume_token(first,'VERIFY')
    assert s.consume_token(second,'VERIFY').pk==user.pk

def test_forgot_generic_and_rate(client,user):
    existing=post(client,'auth/forgot-password',{'email':user.email})
    unknown=post(client,'auth/forgot-password',{'email':'missing@example.com'})
    assert existing.json()==unknown.json() and len(mail.outbox)==1
    for _ in range(2):post(client,'auth/forgot-password',{'email':user.email})
    assert post(client,'auth/forgot-password',{'email':user.email}).status_code==429

def test_reset_one_use_invalidates_all_sessions(client,user):
    signin(client,user);second=Client();signin(second,user)
    raw=s.issue_token(user,'RESET');new='OtherSafe9!pass'
    assert post(Client(),'auth/reset-password',{'token':raw,'password':new,'password_confirm':new}).status_code==200
    assert client.get('/api/me/').status_code==403 and second.get('/api/me/').status_code==403
    assert post(Client(),'auth/reset-password',{'token':raw,'password':new,'password_confirm':new}).status_code==400
    user.refresh_from_db();assert user.check_password(new)

def enable(user):
    setup=s.setup_factor(user);code=pyotp.TOTP(setup['secret']).now()
    return setup,s.enable_factor(user,code)

def test_factor_encryption_replay_and_recovery(user):
    setup,codes=enable(user);tf=TwoFactorSettings.objects.get(user=user)
    assert setup['secret'] not in tf.secret_encrypted and not tf.pending_secret_encrypted
    assert not s.verify_factor(user,pyotp.TOTP(setup['secret']).now())
    with patch('apps.security.services.time.time',return_value=time.time()+30):assert s.verify_factor(user,pyotp.TOTP(setup['secret']).at(time.time()+30))
    assert s.verify_factor(user,codes[0]) and not s.verify_factor(user,codes[0])
    assert RecoveryCode.objects.filter(user=user).count()==10 and not RecoveryCode.objects.filter(digest=codes[0]).exists()

def test_pending_factor_has_no_access(client,user):
    _,codes=enable(user)
    assert signin(client,user).json()['requires_2fa']
    assert client.get('/api/me/').status_code==403
    assert post(client,'auth/two-factor',{'code':codes[0]}).status_code==200
    assert client.get('/api/me/').status_code==200

def test_existing_session_removed_during_factor_login(client,user,admin):
    signin(client,admin);enable(user)
    assert signin(client,user).json()['requires_2fa']
    assert client.get('/api/security/admin/users/').status_code==403

def test_otp_limit_survives_new_challenge(client,user):
    enable(user);signin(client,user)
    for _ in range(5):assert post(client,'auth/two-factor',{'code':'invalid'}).status_code==400
    signin(client,user)
    assert post(client,'auth/two-factor',{'code':'invalid'}).status_code==429

def test_disable_requires_both_and_invalidates_session(client,user):
    _,codes=enable(user);signin(client,user);post(client,'auth/two-factor',{'code':codes[0]})
    assert post(client,'security/2fa/disable',{'password':'wrong','code':codes[1]}).status_code==403
    assert post(client,'security/2fa/disable',{'password':PASSWORD,'code':'bad'}).status_code==400
    assert post(client,'security/2fa/disable',{'password':PASSWORD,'code':codes[1]}).status_code==200
    assert client.get('/api/me/').status_code==403 and not RecoveryCode.objects.exists()

def test_google_does_not_merge_email_and_explicit_link(user):
    claims={'sub':'google-user','email':user.email,'email_verified':True}
    with pytest.raises(Exception):s.resolve_google_identity(request(),claims)
    assert not ExternalIdentity.objects.exists()
    assert s.resolve_google_identity(request(),claims,{'user_id':user.pk,'version':0}).pk==user.pk
    assert s.resolve_google_identity(request(),claims).pk==user.pk

def test_google_unverified_email_and_stale_link(user):
    with pytest.raises(Exception):s.resolve_google_identity(request(),{'sub':'x','email':'x@example.com','email_verified':False})
    with pytest.raises(Exception):s.resolve_google_identity(request(),{'sub':'x','email':'x@example.com','email_verified':True},{'user_id':user.pk,'version':999})

def test_google_new_passwordless_account():
    u=s.resolve_google_identity(request(),{'sub':'x','email':'x@example.com','email_verified':True})
    assert u.email_verified and not u.has_usable_password() and u.role=='TESTER'

def test_oidc_callback_rejects_missing_state(client):
    with patch('apps.security.views.oauth.google.authorize_access_token') as exchange:
        response=client.get('/api/auth/oidc/callback/?code=attacker')
    assert response.status_code==302 and 'error=google' in response.url and not exchange.called

def test_oidc_callback_uri_keeps_an_allowed_local_origin(settings):
    from apps.security.views import oidc_callback_uri
    local = RequestFactory().post('/', HTTP_ORIGIN='http://127.0.0.1:5173')
    other = RequestFactory().post('/', HTTP_ORIGIN='https://evil.example')
    assert oidc_callback_uri(local) == 'http://127.0.0.1:5173/api/auth/oidc/callback/'
    assert oidc_callback_uri(other) == settings.PUBLIC_BASE_URL + '/api/auth/oidc/callback/'

def test_ip_header_untrusted():
    req=request();req.META['HTTP_X_FORWARDED_FOR']='1.2.3.4'
    assert s.ip_of(req)=='127.0.0.1'
    with override_settings(TRUSTED_PROXY_IPS=['127.0.0.1/32']):assert s.ip_of(req)=='1.2.3.4'
