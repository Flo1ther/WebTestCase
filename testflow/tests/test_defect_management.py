import pytest
from apps.projects.models import Project
from apps.test_cases.models import TestCase, TestStep
from apps.executions.models import TestRun
from tests.test_api import client, users


@pytest.mark.django_db
def test_defect_preserves_execution_evidence_and_run_link(client, users):
    project=Project.objects.create(name='Defect project',created_by=users['manager'])
    case=TestCase.objects.create(project=project,title='Checkout',description='d',expected_result='r',created_by=users['manager'])
    TestStep.objects.create(test_case=case,step_number=1,action='a',expected_result='r')
    run=TestRun.objects.create(project=project,name='Release',created_by=users['manager'])
    run.test_cases.add(case)
    client.force_authenticate(users['manager'])
    response=client.post('/api/defects/',{'test_case':case.id,'test_run':run.id,'title':'Invalid token accepted','description':'Checkout returned 201.','reproduction_steps':'POST /checkout with invalid token','expected_result':'HTTP 400','actual_result':'HTTP 201','severity':'CRITICAL','priority':'HIGH','product_version':'1.0','environment':'local demo','status':'OPEN'},format='json')
    assert response.status_code==201
    assert response.data['actual_result']=='HTTP 201' and response.data['test_run']==run.id
