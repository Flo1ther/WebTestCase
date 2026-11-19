"""HTTP integration check against real PostgreSQL, SMTP/Mailpit and Cloudflare test keys."""
import json
import re
import secrets
import time
from pathlib import Path
import requests
import pyotp

ROOT=Path(__file__).resolve().parent.parent
BASE='http://localhost:5173'
MAIL='http://127.0.0.1:18025'
credentials=[json.loads((ROOT/'.local/integration-credentials.json').read_text(encoding='utf-8'))]

def session():
    client=requests.Session();csrf(client);return client
def csrf(client):
    response=client.get(BASE+'/api/csrf/',timeout=15);response.raise_for_status()
    client.headers.update({'X-CSRFToken':response.json()['csrf_token'],'Origin':BASE})
def post(client,path,payload,status=200):
    response=client.post(BASE+'/api/'+path+'/',json=payload,timeout=30)
    assert response.status_code==status,(path,response.status_code,response.text[:160])
    return response.json()
def email_token(email,kind):
    messages=requests.get(MAIL+'/api/v1/messages',timeout=10).json()['messages']
    for message in messages:
        if any(item['Address']==email for item in message['To']):
            body=requests.get(MAIL+'/api/v1/message/'+message['ID'],timeout=10).json()['Text']
            if kind in body:return re.search(r'token=([A-Za-z0-9_-]+)',body).group(1)
    raise AssertionError('Mailpit did not receive the requested email')

admin=session();post(admin,'auth/login',{'email':credentials[0]['email'],'password':credentials[0]['password']});csrf(admin)
project=post(admin,'projects',{'name':'Перевірка інтеграції '+secrets.token_hex(3),'description':'Реальний HTTP-сценарій WebTestCase.'},201)
spec='Назва: Збереження імені\nОпис: Перевірити збереження даних після оновлення.\nПередумови: Користувач увійшов, профіль відкрито.\nКроки:\n1. Увести ім’я Олена та зберегти => Показано повідомлення про збереження.\n2. Оновити сторінку => Ім’я Олена відображається.\nОчікуваний результат: Нове ім’я збережено.'
generated=post(admin,'ai/generate-test-cases',{'feature_description':spec,'count':1},201)
case=post(admin,f'ai/analyses/{generated["id"]}/create-case',{'index':0,'project':project['id']},201)
review=post(admin,'ai/analyze-test-case',{'test_case_id':case['id']},201)
assert review['result']['status']=='no_findings' and not review['result']['improvements']
print('PASS: real project -> structured Ukrainian scenario -> saved test case -> analysis without forced advice.')
client=session();email='live-'+secrets.token_hex(4)+'@demo.local';password='Test9!'+secrets.token_urlsafe(16)
post(client,'auth/register',{'email':email,'first_name':'Інтеграційний','last_name':'Тест','password':password,'password_confirm':password,'captcha_token':'XXXX.DUMMY.TOKEN.XXXX'},201)
post(client,'auth/login',{'email':email,'password':password});csrf(client)
assert client.get(BASE+'/api/me/').status_code==200 and client.get(BASE+'/api/me/').json()['email_verified'] is False
assert client.get(BASE+'/api/projects/').status_code==403
post(client,'auth/logout',{});csrf(client)
raw=email_token(email,'verify-email');post(client,'auth/verify-email',{'token':raw})
post(client,'auth/verify-email',{'token':raw},400)
post(client,'auth/login',{'email':email,'password':password});csrf(client)
assert client.get(BASE+'/api/me/').json()['email']==email
setup=post(client,'security/2fa/setup',{'password':password})
codes=post(client,'security/2fa/enable',{'code':pyotp.TOTP(setup['secret']).now()})['recovery_codes']
post(client,'auth/logout',{});csrf(client)
assert post(client,'auth/login',{'email':email,'password':password})['requires_2fa'];csrf(client)
assert client.get(BASE+'/api/me/').status_code==403
# Advance to the next real TOTP interval, because the setup code is consumed.
wait=31-(time.time()%30)
time.sleep(wait)
post(client,'auth/two-factor',{'code':pyotp.TOTP(setup['secret']).now()});csrf(client)
assert client.get(BASE+'/api/me/').status_code==200
post(client,'auth/logout',{});csrf(client)
post(client,'auth/login',{'email':email,'password':password});csrf(client)
post(client,'auth/two-factor',{'code':codes[0]});csrf(client)
assert client.get(BASE+'/api/security/admin/users/').status_code==403
post(client,'auth/forgot-password',{'email':email})
token=email_token(email,'reset-password');new='NewSafe9!'+secrets.token_urlsafe(16)
visitor=session();post(visitor,'auth/reset-password',{'token':token,'password':new,'password_confirm':new})
assert client.get(BASE+'/api/me/').status_code==403
post(visitor,'auth/reset-password',{'token':token,'password':new,'password_confirm':new},400)
for _ in range(5):post(visitor,'auth/login',{'email':email,'password':'Wrong9!pass'},400)
post(visitor,'auth/login',{'email':email,'password':new},429)
admin=session();post(admin,'auth/login',{'email':credentials[0]['email'],'password':credentials[0]['password']});csrf(admin)
users=admin.get(BASE+'/api/security/admin/users/',params={'search':email}).json()
assert users['count']==1
user=users['results'][0]
post(admin,f'security/admin/users/{user["id"]}',{'blocked':False})
post(admin,f'security/admin/users/{user["id"]}',{'blocked':True})
assert post(visitor,'auth/login',{'email':email,'password':new},403)
post(admin,f'security/admin/users/{user["id"]}',{'blocked':False})
assert admin.get(BASE+'/api/security/admin/events/',params={'email':email}).json()['count']>=10
assert len(admin.get(BASE+'/api/security/admin/dashboard/').json()['timeline'])==30
print('PASS: live CAPTCHA, SMTP/email activation, login, real TOTP, recovery, reset/session revocation, locks, admin audit/dashboard and RBAC.')
print('Integration account remains in PostgreSQL; no credentials or tokens were logged.')
