"""One isolated local account for integration checks; existing users are never altered."""
import os
import sys
import json
import secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
from apps.accounts.models import User
if not settings.DEBUG:raise SystemExit('Перевірка доступна лише в локальному DEBUG-середовищі.')
path=ROOT/'.local/integration-credentials.json'
path.parent.mkdir(exist_ok=True)
if not path.exists():
    suffix=secrets.token_hex(4);password='Check9!'+secrets.token_urlsafe(20)
    user=User.objects.create_user(username='integration_'+suffix,email='integration-'+suffix+'@wtc.local',password=password,role='ADMIN',first_name='Перевірка',last_name='Інтеграції',email_verified=True)
    path.write_text(json.dumps({'email':user.email,'password':password},ensure_ascii=False),encoding='utf-8')
    if os.name!='nt':path.chmod(0o600)
print('Локального користувача перевірки підготовлено. Дані входу: .local/integration-credentials.json; не публікувати.')
