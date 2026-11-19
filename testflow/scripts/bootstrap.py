"""Initialize missing secrets only; preserve existing connection strings and identities."""
from pathlib import Path
import secrets
from urllib.parse import urlsplit,unquote
from cryptography.fernet import Fernet
ROOT=Path(__file__).resolve().parent.parent
path=ROOT/'.env'
text=path.read_text(encoding='utf-8') if path.exists() else (ROOT/'.env.example').read_text(encoding='utf-8')
lines=dict(line.split('=',1) for line in text.splitlines() if '=' in line and not line.startswith('#'))
for key,value in [('SECRET_KEY',secrets.token_urlsafe(48)),('TOTP_ENCRYPTION_KEY',Fernet.generate_key().decode())]:
    old=lines.get(key,'')
    if not old or old.startswith(('replace-','generate-')):
        text=text.replace(key+'='+old,key+'='+value) if key in lines else text+'\n'+key+'='+value
if 'DATABASE_PASSWORD' not in lines:
    url=urlsplit(lines.get('DATABASE_URL',''))
    password=unquote(url.password) if url.password and url.password!='change-me' else secrets.token_urlsafe(24)
    text+='\nDATABASE_PASSWORD='+password+'\n'
    if url.password=='change-me':text=text.replace(':change-me@',':'+password+'@')
path.write_text(text,encoding='utf-8')
print('Секрети середовища підготовлено; наявні параметри збережено.')
