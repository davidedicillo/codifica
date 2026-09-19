import re
import pytest
from dataclasses import replace
from unittest.mock import patch

from fastapi.testclient import TestClient

from server.app import create_app


@pytest.fixture
def settings(settings):
    return replace(settings, sendgrid_api_key='test-only', email_from='hello@example.com')


def test_email_codes_are_single_use_origin_bound_and_private(settings):
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        response = client.post('/api/v1/auth/email/request', json={'email': 'owner@example.com'})
        assert response.status_code == 403
        with patch('httpx.AsyncClient.post') as send:
            send.return_value.status_code = 202
            response = client.post('/api/v1/auth/email/request', json={'email': 'owner@example.com'}, headers={'Origin': settings.origin})
            assert response.status_code == 200
            code = re.search(r'\b\d{6}\b', send.call_args.kwargs['json']['content'][0]['value']).group()
        assert code not in response.text
        with app.state.db.connect() as db:
            assert code not in str([tuple(r) for r in db.execute('SELECT * FROM email_codes')])
        payload = {'code': code, 'name': 'Owner'}
        response = client.post('/api/v1/auth/email/verify', json=payload, headers={'Origin': settings.origin})
        assert response.status_code == 200, response.text
        assert response.json()['user']['email'] == 'owner@example.com'
        assert 'HttpOnly' in response.headers['set-cookie']
        assert client.post('/api/v1/auth/email/verify', json=payload, headers={'Origin': settings.origin}).status_code == 401


def test_email_rate_limits_attempts_and_new_browser_binding(settings):
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        client.headers['Origin'] = settings.origin
        with patch('httpx.AsyncClient.post') as send:
            send.return_value.status_code = 202
            assert client.post('/api/v1/auth/email/request', json={'email': 'owner@example.com'}).status_code == 200
            code = re.search(r'\b\d{6}\b', send.call_args.kwargs['json']['content'][0]['value']).group()
        with TestClient(app, base_url=settings.origin) as other:
            assert other.post('/api/v1/auth/email/verify', json={'code': code, 'name': 'Owner'}, headers={'Origin': settings.origin}).status_code == 401
        assert client.post('/api/v1/auth/email/request', json={'email': 'owner@example.com'}).status_code == 429
        wrong = '000000' if code != '000000' else '111111'
        for _ in range(5):
            assert client.post('/api/v1/auth/email/verify', json={'code': wrong, 'name': 'Owner'}).status_code == 401
        assert client.post('/api/v1/auth/email/verify', json={'code': code, 'name': 'Owner'}).status_code == 401


def test_expired_code_unknown_email_and_delivery_failure(settings):
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        client.headers['Origin'] = settings.origin
        with patch('httpx.AsyncClient.post') as send:
            send.return_value.status_code = 202
            response = client.post('/api/v1/auth/email/request', json={'email': 'stranger@example.com'})
            assert response.status_code == 200
            assert not send.called
            assert client.post('/api/v1/auth/email/request', json={'email': 'owner@example.com'}).status_code == 200
            code = re.search(r'\b\d{6}\b', send.call_args.kwargs['json']['content'][0]['value']).group()
        with app.state.db.transaction() as db:
            db.execute('UPDATE email_codes SET expires=0')
        assert client.post('/api/v1/auth/email/verify', json={'code': code, 'name': 'Owner'}).status_code == 401
        with patch('httpx.AsyncClient.post') as send:
            send.return_value.status_code = 403
            response = client.post('/api/v1/auth/email/request', json={'email': 'other@example.com'})
            assert response.status_code == 503
        assert 'codifica_login' not in response.cookies


def test_sendgrid_can_replace_oidc_in_production(settings):
    production = replace(settings, dev_auth=False, origin='https://codifica.app', sendgrid_api_key='test-only', email_from='hello@example.com')
    production.validate()
    with TestClient(create_app(production), base_url=production.origin) as client:
        assert client.get('/api/v1/auth/config').json()['emailAuth'] is True
        assert client.post('/api/v1/auth/dev-login', json={'email':'owner@example.com','name':'Owner'}).status_code == 403


def test_unknown_addresses_do_not_exhaust_email_delivery_budget(settings):
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        client.headers['Origin'] = settings.origin
        for n in range(105):
            assert client.post('/api/v1/auth/email/request', json={'email': f'unknown{n}@example.com'}).status_code == 200
        with patch('httpx.AsyncClient.post') as send:
            send.return_value.status_code = 202
            assert client.post('/api/v1/auth/email/request', json={'email': 'owner@example.com'}).status_code == 200
