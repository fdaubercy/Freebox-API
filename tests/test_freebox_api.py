# tests/test_freebox_api.py
# Version complète : tests automatisés pour Freebox Dashboard
# - JWT via cookie ou header
# - Tests /status, /wifi, /dhcp, /reboot
# - Compatible FlaskClient sous Windows

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from freebox_dashboard_app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.url_map.strict_slashes = False  # pour éviter 404 sur Windows
    with app.test_client() as client:
        yield client

# --- Fixture pour token JWT ---
@pytest.fixture
def token(client):
    response = client.post('/login', json={'username':'admin','password':'admin'})
    return response.get_json()['token']

# --- Tests Login ---
def test_login_success(client):
    response = client.post('/login', json={'username':'admin','password':'admin'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'token' in data

def test_login_failure(client):
    response = client.post('/login', json={'username':'admin','password':'wrong'})
    assert response.status_code == 401

# --- Tests endpoints API ---
def test_status_unauthorized(client):
    response = client.get('/status')
    assert response.status_code == 401

def test_status_authorized(client, token):
    # Test via header
    response = client.get('/status', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code in [200, 500]
    # Test via cookie
    response2 = client.get('/status', headers={'Cookie': f'jwt={token}'})
    assert response2.status_code in [200, 500]

def test_wifi_authorized(client, token):
    response = client.get('/wifi', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code in [200, 500]

def test_dhcp_authorized(client, token):
    response = client.get('/dhcp', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code in [200, 500]

def test_reboot_authorized(client, token):
    response = client.post('/reboot', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code in [200, 500]

def test_dashboard_access(client, token):
    response = client.get('/dashboard', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert b'Freebox Dashboard' in response.data
