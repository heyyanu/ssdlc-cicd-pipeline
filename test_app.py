import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home(client):
    response = client.get('/')
    assert response.status_code == 200

def test_login_success(client):
    response = client.post('/login', json={
        'username': 'admin',
        'password': 'password123'
    })
    assert response.status_code == 200

def test_login_fail(client):
    response = client.post('/login', json={
        'username': 'admin',
        'password': 'wrongpassword'
    })
    assert response.status_code == 401