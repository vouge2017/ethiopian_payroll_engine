"""Quick Start wizard tests — verify employee import from pasted data."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
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
def company_user(app):
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


@pytest.fixture
def client(app):
    return app.test_client()


def login(client):
    client.post('/auth/login', data={'login_id': '0911000001', 'password': 'Test1234!'}, follow_redirects=True)


def test_quick_start_page_loads(app, company_user, client):
    """Quick Start page loads successfully."""
    login(client)
    resp = client.get('/quick-start')
    assert resp.status_code == 200
    assert b'Quick Start' in resp.data


def test_import_employees_json(app, company_user, client):
    """Import employees via JSON POST."""
    login(client)
    resp = client.post(
        '/quick-start/import',
        json={
            'employees': [
                {'name': 'Abebe Kebede', 'phone': '0911234567', 'salary': 8000},
                {'name': 'Tigist Hailu', 'phone': '0922345678', 'salary': 12000},
            ]
        },
        headers={'Content-Type': 'application/json'},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['imported'] == 2

    with app.app_context():
        employees = Employee.query.filter_by(company_id=company_user[0]).all()
        assert len(employees) == 2
        assert employees[0].name == 'Abebe Kebede'
        assert employees[1].basic_salary == 12000


def test_import_validates_missing_name(app, company_user, client):
    """Import rejects rows with missing name."""
    login(client)
    resp = client.post(
        '/quick-start/import',
        json={
            'employees': [
                {'name': '', 'phone': '0911234567', 'salary': 8000},
                {'name': 'Valid Name', 'phone': '0922345678', 'salary': 5000},
            ]
        },
        headers={'Content-Type': 'application/json'},
    )
    data = resp.get_json()
    assert data['imported'] == 1
    assert len(data['errors']) == 1
    assert 'missing name' in data['errors'][0]


def test_import_validates_negative_salary(app, company_user, client):
    """Import rejects negative salary."""
    login(client)
    resp = client.post(
        '/quick-start/import',
        json={
            'employees': [
                {'name': 'Bad Salary', 'phone': '0911234567', 'salary': -1000},
            ]
        },
        headers={'Content-Type': 'application/json'},
    )
    data = resp.get_json()
    assert data['imported'] == 0
    assert 'negative salary' in data['errors'][0]


def test_import_validates_invalid_salary(app, company_user, client):
    """Import rejects non-numeric salary."""
    login(client)
    resp = client.post(
        '/quick-start/import',
        json={
            'employees': [
                {'name': 'Bad Input', 'phone': '0911234567', 'salary': 'abc'},
            ]
        },
        headers={'Content-Type': 'application/json'},
    )
    data = resp.get_json()
    assert data['imported'] == 0
    assert 'invalid salary' in data['errors'][0]


def test_import_empty_body(app, company_user, client):
    """Import rejects empty request."""
    login(client)
    resp = client.post(
        '/quick-start/import',
        json={},
        headers={'Content-Type': 'application/json'},
    )
    assert resp.status_code == 400


def test_import_generates_employee_ids(app, company_user, client):
    """Import auto-generates employee IDs."""
    login(client)
    resp = client.post(
        '/quick-start/import',
        json={
            'employees': [
                {'name': 'First', 'phone': '0911000001', 'salary': 5000},
                {'name': 'Second', 'phone': '0911000002', 'salary': 6000},
                {'name': 'Third', 'phone': '0911000003', 'salary': 7000},
            ]
        },
        headers={'Content-Type': 'application/json'},
    )
    data = resp.get_json()
    assert data['imported'] == 3

    with app.app_context():
        employees = Employee.query.filter_by(company_id=company_user[0]).order_by(Employee.id).all()
        ids = [e.employee_id for e in employees]
        assert len(ids) == 3
        # IDs should be sequential
        assert all(id.startswith('EMP') for id in ids)


def test_import_max_limit(app, company_user, client):
    """Import rejects more than 500 employees."""
    login(client)
    employees = [{'name': f'Emp {i}', 'salary': 5000} for i in range(501)]
    resp = client.post(
        '/quick-start/import',
        json={'employees': employees},
        headers={'Content-Type': 'application/json'},
    )
    assert resp.status_code == 400
    assert '500' in resp.get_json()['message']
