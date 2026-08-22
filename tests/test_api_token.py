"""API token authentication tests — Bearer token access to /api/v1/ endpoints."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    ApiKey,
    Company,
    Employee,
    OvertimeEntry,
    TenantQuery,
    User,
    UserCompany,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _setup_company_user(app):
    """Create company + owner user + UserCompany link. Returns (company_id, user_id)."""
    with app.app_context():
        company = Company(name='TestCo')
        db.session.add(company)
        db.session.commit()
        user = User(phone='0911000001', company_id=company.id, role='owner')
        user.set_password('Test1234!')
        db.session.add(user)
        db.session.commit()
        uc = UserCompany(user_id=user.id, company_id=company.id, role='owner')
        db.session.add(uc)
        db.session.commit()
        return company.id, user.id


def _create_api_key(app, user_id, company_id, name='Test Key'):
    """Create an API key. Returns (raw_token, key_id)."""
    with app.app_context():
        user = db.session.get(User, user_id)
        key, raw_token = ApiKey.create_for_user(user, company_id, name=name)
        return raw_token, key.id


# --- Token lookup ---


def test_api_key_hash_stored_not_raw(app):
    """Raw token should NOT be stored; only the SHA-256 hash."""
    cid, uid = _setup_company_user(app)
    raw_token, key_id = _create_api_key(app, uid, cid, 'Hash Test')
    with app.app_context():
        key = db.session.get(ApiKey, key_id)
        assert key.token_hash != raw_token
        assert len(key.token_hash) == 64  # SHA-256 hex


def test_api_key_lookup_valid(app):
    """Lookup by raw token returns the key and user."""
    cid, uid = _setup_company_user(app)
    raw_token, _key_id = _create_api_key(app, uid, cid, 'Lookup Test')
    with app.app_context():
        found_key, found_user = ApiKey.lookup(raw_token)
        assert found_key is not None
        assert found_user.id == uid


def test_api_key_lookup_invalid_token(app):
    """Lookup with garbage token returns None."""
    with app.app_context():
        found_key, found_user = ApiKey.lookup('ep_garbage_token')
        assert found_key is None
        assert found_user is None


def test_api_key_lookup_revoked(app):
    """Revoked key should not be found."""
    cid, uid = _setup_company_user(app)
    raw_token, key_id = _create_api_key(app, uid, cid, 'Revoked')
    with app.app_context():
        key = db.session.get(ApiKey, key_id)
        key.revoke()
        found_key, _found_user = ApiKey.lookup(raw_token)
        assert found_key is None


def test_api_key_last_used_updates(app):
    """Lookup should update last_used_at."""
    cid, uid = _setup_company_user(app)
    raw_token, key_id = _create_api_key(app, uid, cid, 'Used')
    with app.app_context():
        key = db.session.get(ApiKey, key_id)
        assert key.last_used_at is None
        ApiKey.lookup(raw_token)
        refreshed = db.session.get(ApiKey, key_id)
        assert refreshed.last_used_at is not None


# --- Bearer token on API endpoints ---


def test_list_employees_with_bearer_token(app):
    """GET /api/v1/employees with valid Bearer token returns 200."""
    cid, uid = _setup_company_user(app)
    raw_token, _ = _create_api_key(app, uid, cid)
    with app.test_client() as client:
        resp = client.get('/api/v1/employees', headers={'Authorization': f'Bearer {raw_token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert 'employees' in data
        assert 'pagination' in data


def test_list_employees_no_auth(app):
    """GET /api/v1/employees with no auth returns 401."""
    with app.test_client() as client:
        resp = client.get('/api/v1/employees')
        assert resp.status_code == 401


def test_list_employees_bad_token(app):
    """GET /api/v1/employees with garbage token returns 401."""
    with app.test_client() as client:
        resp = client.get('/api/v1/employees', headers={'Authorization': 'Bearer ep_invalidtoken123'})
        assert resp.status_code == 401


def test_create_employee_with_bearer_token(app):
    """POST /api/v1/employees with Bearer token creates employee."""
    cid, uid = _setup_company_user(app)
    raw_token, _ = _create_api_key(app, uid, cid)
    with app.test_client() as client:
        resp = client.post(
            '/api/v1/employees',
            headers={'Authorization': f'Bearer {raw_token}'},
            json={
                'employee_id': 'API001',
                'name': 'API Worker',
                'basic_salary': 5000,
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['employee_id'] == 'API001'


def test_impact_endpoint_with_bearer(app):
    """POST /api/v1/impact/salary-raise works with Bearer token."""
    cid, uid = _setup_company_user(app)
    raw_token, _ = _create_api_key(app, uid, cid)
    with app.test_client() as client:
        resp = client.post(
            '/api/v1/impact/salary-raise',
            headers={'Authorization': f'Bearer {raw_token}'},
            json={
                'current_basic': 5000,
                'current_allowances': 1000,
                'new_basic': 6000,
                'new_allowances': 1200,
                'employee_name': 'Test',
            },
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'impact' in data or 'current' in data


# --- API Key management endpoints ---


def test_list_api_keys(app):
    """GET /api/v1/api-keys lists keys for current user."""
    cid, uid = _setup_company_user(app)
    raw_token, _ = _create_api_key(app, uid, cid)
    with app.test_client() as client:
        resp = client.get('/api/v1/api-keys', headers={'Authorization': f'Bearer {raw_token}'})
        assert resp.status_code == 200
        keys = resp.get_json()
        assert len(keys) >= 1
        assert keys[0]['name'] == 'Test Key'


def test_create_api_key_via_api(app):
    """POST /api/v1/api-keys creates a new key and returns raw token."""
    cid, uid = _setup_company_user(app)
    raw_token, _ = _create_api_key(app, uid, cid)
    with app.test_client() as client:
        resp = client.post(
            '/api/v1/api-keys', headers={'Authorization': f'Bearer {raw_token}'}, json={'name': 'CI Pipeline'}
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert 'token' in data
        assert data['token'].startswith('ep_')
        assert data['message'].startswith('Store this token')


def test_revoke_api_key(app):
    """DELETE /api/v1/api-keys/<id> revokes the key."""
    cid, uid = _setup_company_user(app)
    raw_token, key_id = _create_api_key(app, uid, cid)
    with app.test_client() as client:
        resp = client.delete(f'/api/v1/api-keys/{key_id}', headers={'Authorization': f'Bearer {raw_token}'})
        assert resp.status_code == 200
        # Key should no longer work
        resp2 = client.get('/api/v1/employees', headers={'Authorization': f'Bearer {raw_token}'})
        assert resp2.status_code == 401


# --- Tenant isolation via API token ---


def test_api_token_tenant_isolation(app):
    """API token from Company A cannot see Company B's employees."""
    cid, uid = _setup_company_user(app)
    raw_token, _ = _create_api_key(app, uid, cid)
    with app.app_context():
        other_company = Company(name='OtherCo')
        db.session.add(other_company)
        db.session.commit()
        emp = Employee(
            employee_id='OTHER001',
            name='Other Worker',
            basic_salary=3000,
            company_id=other_company.id,
        )
        db.session.add(emp)
        db.session.commit()
    with app.test_client() as client:
        resp = client.get('/api/v1/employees', headers={'Authorization': f'Bearer {raw_token}'})
        assert resp.status_code == 200
        ids = [e['employee_id'] for e in resp.get_json()['employees']]
        assert 'OTHER001' not in ids


# --- Role enforcement via API token ---


def test_api_token_owner_only_delete(app):
    """Non-owner API token cannot DELETE employees."""
    cid, _uid = _setup_company_user(app)
    with app.app_context():
        company = db.session.get(Company, cid)
        # Create an accountant
        acct = User(phone='0911000099', company_id=company.id, role='accountant')
        acct.set_password('Test1234!')
        db.session.add(acct)
        db.session.commit()
        uc = UserCompany(user_id=acct.id, company_id=company.id, role='accountant')
        db.session.add(uc)
        db.session.commit()
        _acct_key, acct_token = ApiKey.create_for_user(acct, company.id, name='Acct Key')
        emp = Employee(
            employee_id='DEL001',
            name='Delete Me',
            basic_salary=1000,
            company_id=company.id,
        )
        db.session.add(emp)
        db.session.commit()
        emp_id = emp.id
    with app.test_client() as client:
        resp = client.delete(f'/api/v1/employees/{emp_id}', headers={'Authorization': f'Bearer {acct_token}'})
        assert resp.status_code == 403
