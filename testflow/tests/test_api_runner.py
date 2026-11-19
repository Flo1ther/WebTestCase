import json
from unittest.mock import Mock, patch
import pytest
from apps.projects.models import Project
from apps.executions.models import APITest, APIExecution
from tests.test_api import client, users


@pytest.mark.django_db
def test_api_runner_records_real_status_assertion_and_audit(client, users):
    project=Project.objects.create(name='API runner project',created_by=users['manager'])
    client.force_authenticate(users['manager'])
    created=client.post('/api/api-tests/',{'project':project.id,'name':'Health','method':'GET','url':'http://127.0.0.1:8000/api/demo-store/health/','expected_status':200,'headers':{},'request_body':{},'json_assertions':[{'path':'status','equals':'ok'}]},format='json')
    assert created.status_code==201
    response=Mock(); response.status=200; response.read.return_value=json.dumps({'status':'ok'}).encode(); response.__enter__=Mock(return_value=response); response.__exit__=Mock(return_value=False)
    with patch('apps.executions.views.urlopen',return_value=response):
        ran=client.post(f'/api/api-tests/{created.data["id"]}/run/',format='json')
    assert ran.status_code==201 and ran.data['status']=='PASSED'
    assert APIExecution.objects.filter(api_test_id=created.data['id'],status='PASSED').exists()


@pytest.mark.django_db
def test_api_test_rejects_non_local_url(client, users):
    project=Project.objects.create(name='SSRF project',created_by=users['manager'])
    client.force_authenticate(users['manager'])
    response=client.post('/api/api-tests/',{'project':project.id,'name':'Forbidden','method':'GET','url':'http://169.254.169.254/latest/meta-data','expected_status':200,'headers':{},'request_body':{},'json_assertions':[]},format='json')
    assert response.status_code==400
