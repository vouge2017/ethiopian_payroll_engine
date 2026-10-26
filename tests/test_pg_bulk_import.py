"""Bulk import + single create ID hardening against a real Alembic-migrated
PostgreSQL. Proves at the real database level:

- duplicate employee IDs (in payload, vs active, vs soft-deleted) are per-row
  errors, never IntegrityError 500s — uq_employee_company_empid spans
  soft-deleted rows on PostgreSQL;
- a JSON-numeric employee_id is a row error, not an AttributeError 500;
- an over-20-character employee_id is a row error before VARCHAR(20) rejects
  it with a driver error;
- generated IDs skip every used ID including soft-deleted rows;
- single create reusing a soft-deleted ID returns 409.

Requires TEST_DATABASE_URL pointing at a disposable PostgreSQL instance;
skips otherwise (SQLite runs are covered by test_bulk_import_hardening.py and
test_create_employee_autoid.py).
"""

import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from alembic import command
from alembic.config import Config

import config
from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, User

PG_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not PG_URL.startswith('postgresql'), reason='Requires disposable TEST_DATABASE_URL')


@pytest.fixture
def pg_session(monkeypatch):
    monkeypatch.setattr(config.TestingConfig, 'SQLALCHEMY_DATABASE_URI', PG_URL)
    app = create_app()
    app.config.update(WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    cfg = Config(str(Path(__file__).resolve().parents[1] / 'migrations/alembic.ini'))
    cfg.set_main_option('script_location', str(Path(__file__).resolve().parents[1] / 'migrations'))
    cfg.set_main_option('sqlalchemy.url', PG_URL)
    with app.app_context():
        command.upgrade(cfg, 'head')
        company = Company(name='Bulk proof ' + uuid4().hex)
        db.session.add(company)
        db.session.flush()
        owner = User(company_id=company.id, email=uuid4().hex + '@example.invalid', role='owner')
        owner.set_password('Synthetic1!')
        db.session.add(owner)
        db.session.commit()
        ids = {'company': company.id, 'user': owner.id}
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(ids['user'])
    yield client, ids, app


def _bulk(client, employees):
    return client.post('/api/v1/employees/bulk', json={'employees': employees})


def test_pg_bulk_duplicate_within_payload_is_row_error(pg_session):
    client, ids, app = pg_session
    resp = _bulk(
        client,
        [
            {'employee_id': 'PGDUP1', 'name': 'First', 'basic_salary': 5000},
            {'employee_id': 'PGDUP1', 'name': 'Second', 'basic_salary': 5000},
        ],
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 1
    assert any('duplicate' in e['error'].lower() and 'PGDUP1' in e['error'] for e in data['errors'])
    with app.app_context():
        count = Employee.query.filter_by(company_id=ids['company'], employee_id='PGDUP1').count()
        assert count == 1


def test_pg_bulk_numeric_employee_id_is_row_error(pg_session):
    client, ids, app = pg_session
    resp = _bulk(client, [{'employee_id': 1, 'name': 'Numeric', 'basic_salary': 5000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 0
    assert any('employee_id' in e['error'] for e in data['errors'])
    with app.app_context():
        count = Employee.query.filter_by(company_id=ids['company'], name='Numeric').count()
        assert count == 0


def test_pg_bulk_overlength_employee_id_is_row_error(pg_session):
    """On PostgreSQL the column really is VARCHAR(20); the route must reject
    the row itself instead of letting the driver fail the batch."""
    client, _ids, _app = pg_session
    resp = _bulk(client, [{'employee_id': 'X' * 21, 'name': 'Long', 'basic_salary': 5000}])
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['imported'] == 0
    assert any('20' in e['error'] or 'long' in e['error'].lower() for e in data['errors'])


def test_pg_bulk_generated_ids_skip_soft_deleted(pg_session):
    client, ids, app = pg_session
    with app.app_context():
        for n in ('EMP001', 'EMP002', 'EMP003'):
            db.session.add(Employee(employee_id=n, name=f'W {n}', basic_salary=5000, company_id=ids['company']))
        db.session.commit()
        gone = Employee.query.filter_by(company_id=ids['company'], employee_id='EMP002').first()
        gone.is_deleted = True
        db.session.commit()
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
    with app.app_context():
        generated = sorted(
            row[0]
            for row in db.session.query(Employee.employee_id)
            .filter(Employee.company_id == ids['company'], Employee.name.in_(['New A', 'New B']))
            .all()
        )
        assert generated == ['EMP004', 'EMP005']


def test_pg_single_create_soft_deleted_id_is_409(pg_session):
    client, ids, app = pg_session
    with app.app_context():
        emp = Employee(employee_id='PGDUP2', name='Gone', basic_salary=5000, company_id=ids['company'])
        db.session.add(emp)
        db.session.commit()
        emp.is_deleted = True
        db.session.commit()
    resp = client.post(
        '/api/v1/employees',
        json={'employee_id': 'PGDUP2', 'name': 'Reuse', 'basic_salary': 5000},
    )
    assert resp.status_code == 409
