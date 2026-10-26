"""Quick Start wizard regression tests: leading-zero phones, warnings,
soft-deleted ID collisions, and the 0-imported error path."""

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
        user = User(phone='911000001', company_id=company.id, role='owner')
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
    client.post('/auth/login', data={'login_id': '911000001', 'password': 'Test1234!'}, follow_redirects=True)


def _import(client, rows):
    return client.post('/quick-start/import', json={'employees': rows}, headers={'Content-Type': 'application/json'})


def test_import_non_dict_row_is_row_error(app, company_user, client):
    """A non-object row must be a row error, not an AttributeError 500."""
    login(client)
    resp = _import(client, ['alice', {'name': 'Valid', 'salary': 5000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 1
    assert any('object' in e.lower() for e in data['errors'])


def test_import_non_dict_body_rejected_400(app, company_user, client):
    login(client)
    resp = client.post('/quick-start/import', json=['x'], headers={'Content-Type': 'application/json'})
    assert resp.status_code == 400


def test_import_infinite_salary_is_row_error(app, company_user, client):
    """JSON Infinity parses in Python and must not be stored as a salary."""
    login(client)
    resp = _import(client, [{'name': 'Ok', 'salary': 5000}, {'name': 'Inf', 'salary': float('inf')}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 1
    assert any('salary' in e.lower() for e in data['errors'])
    # A batch where every row fails takes the wizard's no-import error path.
    resp2 = _import(client, [{'name': 'Inf2', 'salary': float('inf')}])
    assert resp2.status_code == 422
    assert resp2.get_json()['imported'] == 0


def test_import_accepts_leading_zero_phone(app, company_user, client):
    """Phones pasted as 0911234567 must be imported as 911234567."""
    login(client)
    resp = _import(client, [{'name': 'Abebe Kebede', 'phone': '0911234567', 'salary': 8000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['imported'] == 1
    assert data['total_warnings'] == 0
    with app.app_context():
        emp = Employee.query.filter_by(company_id=company_user[0]).one()
        assert emp.phone == '911234567'


def test_import_invalid_phone_imports_without_phone_and_warns(app, company_user, client):
    """An unusable phone must not block the row: import without phone + warning."""
    login(client)
    resp = _import(client, [{'name': 'Bethlehem Girma', 'phone': '12345', 'salary': 8000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['imported'] == 1
    assert data['total_warnings'] == 1
    assert 'phone' in data['warnings'][0]
    with app.app_context():
        emp = Employee.query.filter_by(company_id=company_user[0]).one()
        assert emp.phone is None


def test_import_ids_skip_soft_deleted(app, company_user, client):
    """Generated IDs must skip IDs already used (including soft-deleted)."""
    with app.app_context():
        co = Company.query.get(company_user[0])
        deleted = Employee(employee_id='EMP001', name='Gone', basic_salary=5000, company_id=co.id)
        db.session.add(deleted)
        db.session.commit()
        deleted.is_deleted = True
        deleted.deleted_at = None
        db.session.commit()

    login(client)
    resp = _import(client, [{'name': 'New Hire', 'phone': '911234567', 'salary': 8000}])
    assert resp.status_code == 200
    assert resp.get_json()['imported'] == 1

    with app.app_context():
        new_emp = Employee.with_deleted().filter_by(company_id=company_user[0], name='New Hire').one()
        assert new_emp.employee_id == 'EMP002'


def test_import_zero_rows_returns_422_error(app, company_user, client):
    """If nothing imports the endpoint must say error with row errors, not success."""
    login(client)
    resp = _import(
        client,
        [
            {'name': 'Bad Salary One', 'phone': '911234567', 'salary': -50},
            {'name': 'Bad Salary Two', 'phone': '922345678', 'salary': 'abc'},
        ],
    )
    assert resp.status_code == 422
    data = resp.get_json()
    assert data['status'] == 'error'
    assert data['imported'] == 0
    assert data['total_errors'] == 2
    assert len(data['errors']) == 2


def test_import_skipped_row_emits_no_phone_warning(app, company_user, client):
    """A row skipped for a missing name must NOT warn "imported without phone"."""
    login(client)
    resp = _import(client, [{'name': '', 'phone': '999', 'salary': 8000}])
    assert resp.status_code == 422
    data = resp.get_json()
    assert data['status'] == 'error'
    assert data['imported'] == 0
    assert data['total_errors'] == 1
    assert 'missing name' in data['errors'][0]
    assert data['total_warnings'] == 0
