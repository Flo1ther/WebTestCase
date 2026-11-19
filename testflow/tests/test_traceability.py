import pytest
from apps.projects.models import Project
from apps.test_cases.models import TestCase, TestStep
from tests.test_api import client, users


@pytest.mark.django_db
def test_requirement_traceability_and_project_isolation(client, users):
    first=Project.objects.create(name='Trace one',created_by=users['manager'])
    second=Project.objects.create(name='Trace two',created_by=users['manager'])
    case=TestCase.objects.create(project=first,title='Trace case',description='d',expected_result='r',created_by=users['manager'])
    TestStep.objects.create(test_case=case,step_number=1,action='a',expected_result='r')
    client.force_authenticate(users['manager'])
    good=client.post('/api/requirements/',{'project':first.id,'key':'REQ-1','title':'Checkout','description':'Checkout must validate payment.','priority':'HIGH','status':'APPROVED','test_case_ids':[case.id]},format='json')
    assert good.status_code==201 and good.data['covered'] is True
    invalid=client.post('/api/requirements/',{'project':second.id,'key':'REQ-1','title':'Wrong link','description':'must fail','priority':'HIGH','status':'DRAFT','test_case_ids':[case.id]},format='json')
    assert invalid.status_code==400


@pytest.mark.django_db
def test_test_run_accepts_only_project_cases(client, users):
    first=Project.objects.create(name='Run one',created_by=users['manager'])
    second=Project.objects.create(name='Run two',created_by=users['manager'])
    case=TestCase.objects.create(project=second,title='Other case',description='d',expected_result='r',created_by=users['manager'])
    TestStep.objects.create(test_case=case,step_number=1,action='a',expected_result='r')
    client.force_authenticate(users['manager'])
    result=client.post('/api/test-runs/',{'project':first.id,'name':'Release 1.0','description':'Smoke','status':'DRAFT','test_case_ids':[case.id]},format='json')
    assert result.status_code==400


@pytest.mark.django_db
def test_test_run_starts_with_selected_cases_and_progress(client, users):
    project=Project.objects.create(name='Run progress',created_by=users['manager'])
    case=TestCase.objects.create(project=project,title='Selected case',description='d',expected_result='r',created_by=users['manager'])
    TestStep.objects.create(test_case=case,step_number=1,action='a',expected_result='r')
    client.force_authenticate(users['manager'])
    result=client.post('/api/test-runs/',{'project':project.id,'name':'Release smoke','description':'v1 staging','status':'ACTIVE','test_case_ids':[case.id]},format='json')
    assert result.status_code==201
    assert result.data['progress']=={'total':1,'completed':0,'percent':0}
    assert result.data['test_case_ids']==[case.id]


@pytest.mark.django_db
def test_test_suite_rejects_case_from_another_project(client, users):
    first=Project.objects.create(name='Suite one',created_by=users['manager']); second=Project.objects.create(name='Suite two',created_by=users['manager'])
    case=TestCase.objects.create(project=second,title='Foreign',description='d',expected_result='r',created_by=users['manager'])
    TestStep.objects.create(test_case=case,step_number=1,action='a',expected_result='r')
    client.force_authenticate(users['manager'])
    response=client.post('/api/test-suites/',{'project':first.id,'name':'Smoke','description':'d','test_case_ids':[case.id]},format='json')
    assert response.status_code==400


@pytest.mark.django_db
def test_execution_keeps_immutable_test_case_snapshot(client, users):
    project=Project.objects.create(name='Snapshot project',created_by=users['manager'])
    case=TestCase.objects.create(project=project,title='Original title',description='Original description',preconditions='Signed in',expected_result='Visible dashboard',created_by=users['manager'],assigned_to=users['tester'])
    TestStep.objects.create(test_case=case,step_number=1,action='Open dashboard',expected_result='Dashboard is visible')

    client.force_authenticate(users['tester'])
    response=client.post('/api/executions/',{'test_case':case.id,'status':'PASSED','actual_result':'Passed in staging','comment':'ok'},format='json')
    assert response.status_code==201
    assert response.data['test_case_snapshot']['title']=='Original title'
    assert response.data['test_case_snapshot']['steps'][0]['action']=='Open dashboard'
    case.title='Changed later'; case.save(update_fields=['title'])
    history=client.get('/api/executions/')
    assert history.status_code==200
    assert history.data['results'][0]['test_case_snapshot']['title']=='Original title'


@pytest.mark.django_db
def test_tester_cannot_change_requirement_or_test_run(client, users):
    project=Project.objects.create(name='Role isolation',created_by=users['manager'])
    case=TestCase.objects.create(project=project,title='Assigned',description='d',expected_result='r',created_by=users['manager'],assigned_to=users['tester'])
    TestStep.objects.create(test_case=case,step_number=1,action='a',expected_result='r')
    client.force_authenticate(users['manager'])
    requirement=client.post('/api/requirements/',{'project':project.id,'key':'REQ-ROLE-1','title':'Role rule','description':'d','priority':'MEDIUM','status':'DRAFT','test_case_ids':[case.id]},format='json')
    test_run=client.post('/api/test-runs/',{'project':project.id,'name':'Role run','status':'ACTIVE','test_case_ids':[case.id]},format='json')
    client.force_authenticate(users['tester'])
    assert client.patch(f'/api/requirements/{requirement.data["id"]}/',{'title':'Not allowed'},format='json').status_code==403
    assert client.patch(f'/api/test-runs/{test_run.data["id"]}/',{'name':'Not allowed'},format='json').status_code==403
