import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_demo_store_health_and_documented_checkout_defect():
    client = APIClient()
    assert client.get('/api/demo-store/health/').status_code == 200
    response = client.post('/api/demo-store/checkout/', {'items': [{'price': 100, 'quantity': 2}], 'payment_token': 'invalid-token'}, format='json')
    assert response.status_code == 201
    assert response.data['status'] == 'paid'
    assert response.data['total'] == 200


@pytest.mark.django_db
def test_demo_store_rejects_empty_cart():
    assert APIClient().post('/api/demo-store/checkout/', {'items': []}, format='json').status_code == 400
