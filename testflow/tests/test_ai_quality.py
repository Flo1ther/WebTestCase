import json
from urllib.error import URLError
from unittest.mock import Mock,patch
import pytest
from apps.ai_assistant.services import AIService,AIProviderUnavailable
from apps.ai_assistant.models import AIAnalysis
from apps.test_cases.models import TestCase as CaseModel,TestStep as StepModel
from apps.projects.models import Project
from tests.test_api import client,users,test_case

SPEC='''Назва: Збереження імені профілю
Опис: Перевірити збереження нового імені після оновлення сторінки.
Передумови: Користувач увійшов, email підтверджено, профіль відкрито.
Кроки:
1. Увести ім’я Олена та натиснути Зберегти => Показано повідомлення Успішно збережено.
2. Оновити сторінку => У полі імені відображається Олена.
Очікуваний результат: Ім’я збережене та доступне після перезавантаження сторінки.'''

@pytest.fixture(autouse=True)
def local(monkeypatch):monkeypatch.setenv('AI_PROVIDER','local')

def test_full_ukrainian_scenario_has_no_forced_advice():
    service=AIService();generated=service.generate_test_cases(SPEC,3)
    assert len(generated['suggestions'])==1
    scenario=generated['suggestions'][0]
    assert scenario['steps'][0]['action']=='Увести ім’я Олена та натиснути Зберегти'
    result=service._local_analysis(scenario)
    assert result['status']=='no_findings' and result['risks']==[] and result['improvements']==[] and result['optional_suggestions']==[]

def test_single_complete_positive_step_is_valid():
    scenario=AIService().generate_test_cases(SPEC,1)['suggestions'][0];scenario['steps']=scenario['steps'][:1]
    assert AIService()._local_analysis(scenario)['findings']==[]

def test_only_actual_missing_step_result_is_reported():
    scenario=AIService().generate_test_cases(SPEC,1)['suggestions'][0];scenario['steps'][1]['expected_result']=''
    result=AIService()._local_analysis(scenario)
    assert [f['field'] for f in result['findings']]==['steps.1.expected_result']

def test_unstructured_local_request_requests_details_not_fake_cases():
    result=AIService().generate_test_cases('Перевірити оформлення замовлення в магазині',3)
    assert result['suggestions']==[] and result['needs_input']

def test_external_missing_key_does_not_silently_use_rules(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','external');monkeypatch.delenv('AI_API_KEY',raising=False)
    with pytest.raises(AIProviderUnavailable):AIService().generate_test_cases(SPEC,1)
    assert not AIService().configuration()['configured']

def test_ollama_uses_local_llm_json_contract(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama');monkeypatch.setenv('AI_MODEL','qwen2.5:3b')
    response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
    response.read.return_value=json.dumps({'message':{'content':json.dumps({'summary':'Модель отримала вимогу.','suggestions':[],'needs_input':['Уточніть кроки.']})}}).encode()
    with patch('apps.ai_assistant.services.urlopen',return_value=response):
        result=AIService().generate_test_cases('Перевірити зміну email користувача.',1)
    assert result['mode']=='ollama' and result['needs_input']==['Уточніть кроки.']

def test_ollama_generator_falls_back_to_requested_details(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama')
    with patch('apps.ai_assistant.services.urlopen',side_effect=URLError('offline')):
        result=AIService().generate_test_cases('тестування',3)
    assert result['mode']=='deterministic_fallback' and result['suggestions']==[] and result['needs_input']

def test_ollama_text_analysis_requires_quoted_evidence(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama');monkeypatch.setenv('AI_MODEL','qwen2.5:3b')
    response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
    answer={'summary':'Знайдено помилку в сумі.','findings':[{'field':'text','evidence':'28000 грн','reason':'10% від 31000 грн дорівнює 3100 грн, тому сума інша.','recommendation':'Уточнити очікувану суму 27900 грн.'}],'optional_suggestions':[]}
    response.read.return_value=json.dumps({'message':{'content':json.dumps(answer)}}).encode()
    with patch('apps.ai_assistant.services.urlopen',return_value=response):
        result=AIService().analyze_text('Загальна вартість 31000 грн. Після знижки 10% сума 28000 грн.')
    assert result['findings'][0]['evidence']=='28000 грн' and result['status']=='needs_review'

@pytest.mark.django_db
def test_review_keeps_formal_findings_when_ollama_is_unavailable(test_case, monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama');monkeypatch.setenv('AI_MODEL','missing-model')
    test_case.expected_result='Оплату успішно виконано.';test_case.save()
    step=test_case.steps.first();step.action='Ввести невалідний номер картки';step.save()
    with patch('apps.ai_assistant.services.urlopen',side_effect=URLError('offline')):
        result=AIService().analyze_test_case(test_case)
    assert result['mode']=='deterministic_fallback' and any(item['id']=='LOG-INVALID-SUCCESS' for item in result['findings'])

@pytest.mark.django_db
def test_generate_accept_analyze_round_trip_no_advice(client,users):
    client.force_authenticate(users['manager'])
    project=Project.objects.create(name='Проєкт перевірки ШІ',created_by=users['manager'])
    generated=client.post('/api/ai/generate-test-cases/',{'feature_description':SPEC,'count':1},format='json')
    assert generated.status_code==201
    pk=generated.data['id']
    saved=client.post(f'/api/ai/analyses/{pk}/create-case/',{'index':0,'project':project.pk},format='json')
    assert saved.status_code==201
    case=CaseModel.objects.get(pk=saved.data['id'])
    assert case.steps.count()==2 and 'Олена' in case.steps.first().action and case.status=='NOT_RUN'
    repeat=client.post(f'/api/ai/analyses/{pk}/create-case/',{'index':0,'project':project.pk},format='json')
    assert repeat.status_code==200 and CaseModel.objects.filter(project=project).count()==1
    reviewed=client.post('/api/ai/analyze-test-case/',{'test_case_id':case.pk},format='json')
    assert reviewed.status_code==201 and reviewed.data['result']['findings']==[] and reviewed.data['result']['status']=='no_findings'
    assert reviewed.data['result']['test_case_updated_at']==case.updated_at.isoformat()
    client.force_authenticate(users['tester'])
    assert client.post(f'/api/ai/analyses/{pk}/create-case/',{'index':0,'project':project.pk},format='json').status_code==403

@pytest.mark.django_db
def test_text_analysis_is_saved_without_creating_a_test_case(client,users):
    client.force_authenticate(users['manager'])
    result=client.post('/api/ai/analyze-text/',{'scenario':'Перевірити 10% знижку для замовлення.'},format='json')
    assert result.status_code==201 and result.data['test_case'] is None
    assert AIAnalysis.objects.filter(pk=result.data['id'],analysis_type='ANALYZE',test_case__isnull=True).exists()

@pytest.mark.django_db
def test_external_findings_require_real_evidence(test_case,monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','external');monkeypatch.setenv('AI_API_KEY','test-only-key')
    response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
    response.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps({'summary':'Вигаданий недолік','findings':[{'field':'title','evidence':'такої цитати немає','reason':'x','recommendation':'y'}],'optional_suggestions':[]})}}]}).encode()
    with patch('apps.ai_assistant.services.urlopen',return_value=response),pytest.raises(AIProviderUnavailable):AIService().analyze_test_case(test_case)

@pytest.mark.django_db
def test_unverified_user_cannot_reach_existing_modules(client,users):
    user=users['tester'];user.email_verified=False;user.save();client.force_authenticate(user)
    for path in ['/api/projects/','/api/test-cases/','/api/executions/','/api/analytics/overview/','/api/ai/config/']:
        assert client.get(path).status_code==403,path

@pytest.mark.django_db
def test_manager_can_list_assignable_testers_but_not_admin_users(client,users):
    client.force_authenticate(users['manager'])
    result=client.get('/api/assignable-testers/')
    assert result.status_code==200 and result.data['count']==2
    assert all('email' not in u and 'two_factor_enabled' not in u for u in result.data['results'])
    assert client.get('/api/users/').status_code==403
