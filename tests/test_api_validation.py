"""API schema validation tests — strict type/range checks for employee endpoints."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, OvertimeEntry, TenantQuery, User


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
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def company_user(ctx):
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()
    user = User(phone='0911000001', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    return company, user


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    client.post('/auth/login', data={'login_id': '0911000001', 'password': 'Test1234!'}, follow_redirects=True)


# --- POST /api/v1/employees validation ---


def test_create_employee_missing_body(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={})
    assert resp.status_code == 422
    assert 'details' in resp.get_json()


def test_create_employee_missing_employee_id(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'name': 'Test'})
    assert resp.status_code == 422
    details = resp.get_json()['details']
    assert any('employee_id' in d for d in details)


def test_create_employee_missing_name(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': 'E001'})
    assert resp.status_code == 422
    details = resp.get_json()['details']
    assert any('name' in d for d in details)


def test_create_employee_empty_employee_id(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': '', 'name': 'Test'})
    assert resp.status_code == 422


def test_create_employee_negative_salary(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': 'E001', 'name': 'Test', 'basic_salary': -5000})
    assert resp.status_code == 422
    details = resp.get_json()['details']
    assert any('basic_salary' in d for d in details)


def test_create_employee_negative_allowances(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': 'E001', 'name': 'Test', 'allowances': -100})
    assert resp.status_code == 422
    details = resp.get_json()['details']
    assert any('allowances' in d for d in details)


def test_create_employee_invalid_tin_letters(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': 'E001', 'name': 'Test', 'tin': 'ABCD123456'})
    assert resp.status_code == 422
    details = resp.get_json()['details']
    assert any('TIN' in d for d in details)


def test_create_employee_invalid_tin_short(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': 'E001', 'name': 'Test', 'tin': '12345'})
    assert resp.status_code == 422


def test_create_employee_valid_succeeds(client, company_user):
    login(client)
    resp = client.post(
        '/api/v1/employees',
        json={
            'employee_id': 'E001',
            'name': 'Dawit Mekonnen',
            'basic_salary': 10000,
            'allowances': 2000,
            'tin': '1234567890',
        },
    )
    assert resp.status_code == 201


# --- PUT /api/v1/employees/<id> validation ---


def test_update_employee_invalid_salary(client, company_user):
    login(client)
    # Create employee first
    resp = client.post('/api/v1/employees', json={'employee_id': 'E001', 'name': 'Dawit', 'basic_salary': 5000})
    emp_id = resp.get_json()['id']

    resp = client.put(f'/api/v1/employees/{emp_id}', json={'basic_salary': -1000})
    assert resp.status_code == 422
    details = resp.get_json()['details']
    assert any('basic_salary' in d for d in details)


def test_update_employee_valid_partial(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': 'E001', 'name': 'Dawit', 'basic_salary': 5000})
    emp_id = resp.get_json()['id']

    resp = client.put(f'/api/v1/employees/{emp_id}', json={'allowances': 500})
    assert resp.status_code == 200


def test_create_employee_name_too_long(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': 'E001', 'name': 'A' * 101, 'basic_salary': 5000})
    assert resp.status_code == 422
    details = resp.get_json()['details']
    assert any('100 characters' in d for d in details)


def test_create_employee_employee_id_too_long(client, company_user):
    login(client)
    resp = client.post('/api/v1/employees', json={'employee_id': 'E' * 21, 'name': 'Test', 'basic_salary': 5000})
    assert resp.status_code == 422
    details = resp.get_json()['details']
    assert any('20 characters' in d for d in details)
