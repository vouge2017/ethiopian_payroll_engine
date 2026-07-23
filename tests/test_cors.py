"""Tests for CORS configuration.

Verifies:
- No CORS headers by default (same-origin only)
- CORS headers present when CORS_ALLOWED_ORIGINS is set
- Wildcard origin never used with credentials
- Preflight (OPTIONS) handled correctly
- Allowed methods/headers are correct
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User


@pytest.fixture
def app_no_cors():
    """App with no CORS origins configured (default)."""
    env = {k: v for k, v in os.environ.items() if 'CORS' not in k}
    env.pop('CORS_ALLOWED_ORIGINS', None)
    os.environ.pop('CORS_ALLOWED_ORIGINS', None)
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def app_with_cors():
    """App with CORS origins configured."""
    os.environ['CORS_ALLOWED_ORIGINS'] = 'https://app.ethiopayroll.com,https://staging.ethiopayroll.com'
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    os.environ.pop('CORS_ALLOWED_ORIGINS', None)


def _create_user(app):
    with app.app_context():
        company = Company(name='CorsTestCo')
        db.session.add(company)
        db.session.flush()
        owner = User(phone='0910000000', role='owner', company_id=company.id)
        owner.set_password('OwnerPass1!')
        db.session.add(owner)
        db.session.commit()


class TestCorsDefault:
    """No CORS origins configured — same-origin only."""

    def test_no_cors_headers_without_origin(self, app_no_cors):
        """No CORS headers when no Origin header in request."""
        _create_user(app_no_cors)
        client = app_no_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get('/api/v1/employees')
        assert 'Access-Control-Allow-Origin' not in resp.headers

    def test_no_cors_headers_with_origin(self, app_no_cors):
        """No CORS headers even with Origin header (no origins configured)."""
        _create_user(app_no_cors)
        client = app_no_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get('/api/v1/employees', headers={'Origin': 'https://evil.com'})
        # With no CORS_ALLOWED_ORIGINS, flask-cors isn't loaded, so no headers
        assert 'Access-Control-Allow-Origin' not in resp.headers

    def test_web_routes_work_normally(self, app_no_cors):
        """Web routes still work without CORS."""
        _create_user(app_no_cors)
        client = app_no_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get('/help')
        assert resp.status_code == 200


class TestCorsConfigured:
    """CORS origins configured — cross-origin access enabled."""

    def test_cors_headers_with_allowed_origin(self, app_with_cors):
        """CORS headers present for configured origin."""
        _create_user(app_with_cors)
        client = app_with_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get('/api/v1/employees', headers={
            'Origin': 'https://app.ethiopayroll.com',
        })
        assert resp.headers.get('Access-Control-Allow-Origin') == 'https://app.ethiopayroll.com'

    def test_cors_rejects_disallowed_origin(self, app_with_cors):
        """CORS headers NOT present for unconfigured origin."""
        _create_user(app_with_cors)
        client = app_with_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get('/api/v1/employees', headers={
            'Origin': 'https://evil.com',
        })
        assert 'Access-Control-Allow-Origin' not in resp.headers

    def test_cors_allows_credentials(self, app_with_cors):
        """Access-Control-Allow-Credentials is set for allowed origins."""
        _create_user(app_with_cors)
        client = app_with_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get('/api/v1/employees', headers={
            'Origin': 'https://app.ethiopayroll.com',
        })
        assert resp.headers.get('Access-Control-Allow-Credentials') == 'true'

    def test_cors_preflight(self, app_with_cors):
        """OPTIONS preflight request returns correct CORS headers."""
        _create_user(app_with_cors)
        client = app_with_cors.test_client()
        resp = client.options('/api/v1/employees', headers={
            'Origin': 'https://app.ethiopayroll.com',
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Authorization',
        })
        assert resp.headers.get('Access-Control-Allow-Origin') == 'https://app.ethiopayroll.com'
        allowed_methods = resp.headers.get('Access-Control-Allow-Methods', '')
        assert 'GET' in allowed_methods

    def test_cors_exposes_pagination_headers(self, app_with_cors):
        """Custom pagination headers are exposed to the client."""
        _create_user(app_with_cors)
        client = app_with_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get('/api/v1/employees', headers={
            'Origin': 'https://app.ethiopayroll.com',
        })
        exposed = resp.headers.get('Access-Control-Expose-Headers', '')
        assert 'X-Total-Count' in exposed or 'X-Page-Count' in exposed

    def test_cors_both_origins_work(self, app_with_cors):
        """Both configured origins are accepted."""
        _create_user(app_with_cors)
        client = app_with_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})

        resp1 = client.get('/api/v1/employees', headers={
            'Origin': 'https://app.ethiopayroll.com',
        })
        assert resp1.headers.get('Access-Control-Allow-Origin') == 'https://app.ethiopayroll.com'

        resp2 = client.get('/api/v1/employees', headers={
            'Origin': 'https://staging.ethiopayroll.com',
        })
        assert resp2.headers.get('Access-Control-Allow-Origin') == 'https://staging.ethiopayroll.com'

    def test_no_wildcard_with_credentials(self, app_with_cors):
        """Access-Control-Allow-Origin is never '*' when credentials are allowed."""
        _create_user(app_with_cors)
        client = app_with_cors.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get('/api/v1/employees', headers={
            'Origin': 'https://app.ethiopayroll.com',
        })
        origin = resp.headers.get('Access-Control-Allow-Origin', '')
        assert origin != '*', 'CORS wildcard with credentials is a security hole'
