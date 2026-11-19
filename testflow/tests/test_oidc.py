"""Exercise Authlib's actual ID-token signature and claims validation with local RSA keys."""
import time
from unittest.mock import patch
import pytest
from authlib.jose import JsonWebKey, jwt
from apps.security.oidc import oauth

@pytest.fixture
def keys(): return JsonWebKey.generate_key('RSA',2048,is_private=True)

@pytest.mark.parametrize('invalid',['none','issuer','audience','nonce','expired','signature'])
def test_authlib_validates_id_token(keys,invalid):
    now=int(time.time())
    claims={'iss':'https://accounts.google.com','sub':'123','aud':'test-client','iat':now,'exp':now+300,'nonce':'expected-nonce','email':'test@example.com','email_verified':True}
    if invalid=='issuer':claims['iss']='https://evil.example'
    if invalid=='audience':claims['aud']='other-client'
    if invalid=='nonce':claims['nonce']='attacker-nonce'
    if invalid=='expired':claims['exp']=now-600
    signing=JsonWebKey.generate_key('RSA',2048,is_private=True) if invalid=='signature' else keys
    token={'id_token':jwt.encode({'alg':'RS256'},claims,signing).decode(),'access_token':'unused-access-token'}
    google=oauth.google
    with patch.object(google,'client_id','test-client'),patch.object(google,'load_server_metadata',return_value={'issuer':'https://accounts.google.com','id_token_signing_alg_values_supported':['RS256']}),patch.object(google,'create_load_key',return_value=lambda header,payload:keys.as_dict(is_private=False)):
        if invalid=='none':assert google.parse_id_token(token,'expected-nonce')['sub']=='123'
        else:
            with pytest.raises(Exception):google.parse_id_token(token,'expected-nonce')
