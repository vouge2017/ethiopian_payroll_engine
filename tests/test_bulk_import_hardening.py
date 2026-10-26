"""Bulk employee import hardening: /api/v1/employees/bulk must reject bad
employee IDs with per-row errors instead of a 500, and generated IDs must
never collide with any ID ever used for the tenant, including soft-deleted
rows (uq_employee_company_empid covers soft-deleted rows).

Reproduces the parked idea: a numeric employee ID (Excel turns "0001" into
1) and duplicate IDs must not reach the database as silent corruption.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, TenantQuery, User, UserCompany


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        yield app
        db.drop_all()


@pytest.fixture
def owner_session(app):
    with app.app_context():
        co = Company(name='BulkCo')
        db.session.add(co)
        db.session.flush()

        owner = User(phone='0911111111', company_id=co.id, role='owner')
        owner.set_password('Test1234!')
        db.session.add(owner)
        db.session.commit()

        db.session.add(UserCompany(user_id=owner.id, company_id=co.id, role='owner'))
        db.session.commit()

        yield {'co': co, 'owner': owner}


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client):
    client.post(
        '/auth/login',
        data={'login_id': '0911111111', 'password': 'Test1234!'},
        follow_redirects=True,
    )


def _bulk(client, employees):
    return client.post('/api/v1/employees/bulk', json={'employees': employees})


# --- Bad employee_id values are per-row errors, not crashes ---


def test_numeric_employee_id_is_row_error_not_crash(client, owner_session):
    """employee_id arriving as a JSON number (Excel "0001" -> 1) must be a
    per-row error, never an AttributeError 500."""
    _login(client)
    resp = _bulk(client, [{'employee_id': 1, 'name': 'Numeric ID', 'basic_salary': 5000}])
    assert resp.status_code == 200, 'bulk import must not crash on a numeric employee_id'
    data = resp.get_json()
    assert data['imported'] == 0
    assert any('employee_id' in e['error'] for e in data['errors'])


def test_overlength_employee_id_is_row_error(client, owner_session):
    """The column is VARCHAR(20); PostgreSQL rejects longer values with a
    driver error. The route must catch this as a row error."""
    _login(client)
    resp = _bulk(client, [{'employee_id': 'X' * 21, 'name': 'Long ID', 'basic_salary': 5000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 0
    assert any('20' in e['error'] or 'long' in e['error'].lower() for e in data['errors'])


# --- Duplicate IDs are per-row errors, never IntegrityError 500s ---


def test_duplicate_id_within_payload_is_row_error(client, owner_session):
    _login(client)
    resp = _bulk(
        client,
        [
            {'employee_id': 'EMP-D1', 'name': 'First', 'basic_salary': 5000},
            {'employee_id': 'EMP-D1', 'name': 'Second', 'basic_salary': 5000},
        ],
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 1
    assert any('duplicate' in e['error'].lower() and 'EMP-D1' in e['error'] for e in data['errors'])


def test_duplicate_id_against_existing_employee_row_error(client, owner_session):
    co = owner_session['co']
    db.session.add(Employee(employee_id='EMP-D2', name='Existing', basic_salary=5000, company_id=co.id))
    db.session.commit()
    _login(client)
    resp = _bulk(client, [{'employee_id': 'EMP-D2', 'name': 'Clash', 'basic_salary': 5000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 0
    assert any('duplicate' in e['error'].lower() for e in data['errors'])


def test_duplicate_id_against_soft_deleted_row_error(client, owner_session):
    """uq_employee_company_empid spans soft-deleted rows, so a deleted
    employee's ID must still be reported as a duplicate, not a 500."""
    co = owner_session['co']
    emp = Employee(employee_id='EMP-D3', name='Gone', basic_salary=5000, company_id=co.id)
    db.session.add(emp)
    db.session.commit()
    emp.is_deleted = True
    db.session.commit()
    _login(client)
    resp = _bulk(client, [{'employee_id': 'EMP-D3', 'name': 'Back again', 'basic_salary': 5000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 0
    assert any('duplicate' in e['error'].lower() for e in data['errors'])


# --- Generated IDs skip every used ID, including soft-deleted ---


def test_generated_ids_skip_used_including_soft_deleted(client, owner_session):
    """The Quick Start wizard already skips used IDs; the bulk endpoint's
    fallback generator counted only active rows and could regenerate the ID
    of a soft-deleted employee (IntegrityError on commit)."""
    co = owner_session['co']
    for n in ('EMP001', 'EMP002', 'EMP003'):
        db.session.add(Employee(employee_id=n, name=f'W {n}', basic_salary=5000, company_id=co.id))
    db.session.commit()
    gone = Employee.query.filter_by(company_id=co.id, employee_id='EMP002').first()
    gone.is_deleted = True
    db.session.commit()
    _login(client)
    resp = _bulk(
        client,
        [
            {'name': 'New A', 'basic_salary': 5000},
            {'name': 'New B', 'basic_salary': 5000},
        ],
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 2
    assert data['total_errors'] == 0
    ids = sorted(
        row[0]
        for row in db.session.query(Employee.employee_id)
        .filter(Employee.company_id == co.id, Employee.name.in_(['New A', 'New B']))
        .all()
    )
    assert ids == ['EMP004', 'EMP005']


# --- Existing behavior locked in ---


def test_empty_employee_id_autogenerates(client, owner_session):
    _login(client)
    resp = _bulk(client, [{'employee_id': '', 'name': 'Auto', 'basic_salary': 5000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 1
    emp = Employee.query.filter_by(company_id=owner_session['co'].id, name='Auto').first()
    assert emp.employee_id == 'EMP001'


def test_numeric_salary_still_imports(client, owner_session):
    _login(client)
    resp = _bulk(client, [{'name': 'Salary Int', 'basic_salary': 8000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 1


# --- Malformed payloads are 4xx with reasons, never 500s ---


def test_bulk_non_dict_row_is_row_error(client, owner_session):
    """A non-object row (e.g. a bare string) must be a row error, not an
    AttributeError 500 mid-loop."""
    _login(client)
    resp = _bulk(client, ['alice', {'name': 'Valid Row', 'basic_salary': 5000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 1
    assert any('object' in e['error'].lower() for e in data['errors'])
    assert data['errors'][0]['row'] == 1


def test_bulk_non_dict_body_rejected_400(client, owner_session):
    _login(client)
    resp = client.post('/api/v1/employees/bulk', json=['not', 'a', 'dict'])
    assert resp.status_code == 400


def test_bulk_infinite_salary_is_row_error(client, owner_session):
    """JSON Infinity parses fine in Python and would otherwise be stored as
    an infinite basic_salary; it must be a row error."""
    _login(client)
    resp = _bulk(client, [{'name': 'Inf Salary', 'basic_salary': float('inf')}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 0
    assert any('salary' in e['error'].lower() for e in data['errors'])
