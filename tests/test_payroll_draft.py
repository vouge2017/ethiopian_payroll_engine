"""
PayrollDraft tests — proves that payroll data survives in the database
instead of being lost when a Flask session expires.

This is the fix for the session-based data loss bug.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, PayrollDraft, PayrollRun


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def _create_company_and_run():
    """Helper: create a company and payroll run."""
    company = Company(name='Test Company')
    db.session.add(company)
    db.session.commit()
    run = PayrollRun(company_id=company.id, status='review')
    db.session.add(run)
    db.session.commit()
    return company, run


# ---------------------------------------------------------------
# TEST 1: PayrollDraft stores and retrieves data correctly
# ---------------------------------------------------------------
def test_draft_store_and_retrieve(ctx):
    """Data stored in PayrollDraft can be retrieved intact."""
    _company, run = _create_company_and_run()

    sample_data = [
        {
            'id': 'EMP001',
            'name': 'Alice',
            'basic': 8000,
            'allowances': 2000,
            'gross': 10000,
            'taxable': 9440,
            'tax': 1959.0,
            'pension_employee': 560,
            'pension_employer': 880,
            'net': 7481.0,
            'bank': 'telebirr:0911111111',
        },
        {
            'id': 'EMP002',
            'name': 'Bob',
            'basic': 12000,
            'allowances': 3000,
            'gross': 15000,
            'taxable': 14160,
            'tax': 2901.0,
            'pension_employee': 840,
            'pension_employer': 1320,
            'net': 11259.0,
            'bank': 'bank:cbe',
        },
    ]

    draft = PayrollDraft(payroll_run_id=run.id, company_id=run.company_id, employee_data=sample_data)
    db.session.add(draft)
    db.session.commit()

    # Retrieve
    retrieved = PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).first()
    assert retrieved is not None
    assert len(retrieved.employee_data) == 2
    assert retrieved.employee_data[0]['id'] == 'EMP001'
    assert retrieved.employee_data[0]['gross'] == 10000
    assert retrieved.employee_data[1]['id'] == 'EMP002'
    assert retrieved.employee_data[1]['net'] == 11259.0


# ---------------------------------------------------------------
# TEST 2: Draft survives "session expiry" (simulated by new request)
# ---------------------------------------------------------------
def test_draft_survives_session_expiry(ctx):
    """
    The whole point: data persists in DB even if the user's browser
    session expires. Simulate by creating draft, then reading it
    in a completely separate query context.
    """
    _company, run = _create_company_and_run()

    sample_data = [
        {
            'id': 'EMP001',
            'name': 'Alice',
            'basic': 5000,
            'allowances': 0,
            'gross': 5000,
            'taxable': 4650,
            'tax': 472.5,
            'pension_employee': 350,
            'pension_employer': 550,
            'net': 4177.5,
            'bank': 'cash',
        }
    ]

    draft = PayrollDraft(payroll_run_id=run.id, company_id=run.company_id, employee_data=sample_data)
    db.session.add(draft)
    db.session.commit()
    draft_id = draft.id

    # Simulate session expiry: clear SQLAlchemy identity map
    db.session.expire_all()

    # New "request" — read from DB fresh
    fresh_draft = db.session.get(PayrollDraft, draft_id)
    assert fresh_draft is not None
    assert fresh_draft.employee_data[0]['id'] == 'EMP001'
    assert fresh_draft.employee_data[0]['net'] == 4177.5


# ---------------------------------------------------------------
# TEST 3: Draft can be deleted after approval
# ---------------------------------------------------------------
def test_draft_cleanup_after_approval(ctx):
    """After payroll is approved, draft should be deleted."""
    _company, run = _create_company_and_run()

    draft = PayrollDraft(payroll_run_id=run.id, company_id=run.company_id, employee_data=[{'id': 'EMP001'}])
    db.session.add(draft)
    db.session.commit()

    # Simulate approval cleanup
    PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).delete()
    db.session.commit()

    assert PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).first() is None


# ---------------------------------------------------------------
# TEST 4: Draft relationship with PayrollRun works
# ---------------------------------------------------------------
def test_draft_relationship(ctx):
    """PayrollRun.draft should return the associated draft."""
    _company, run = _create_company_and_run()

    draft = PayrollDraft(payroll_run_id=run.id, company_id=run.company_id, employee_data=[{'id': 'EMP001'}])
    db.session.add(draft)
    db.session.commit()

    assert run.draft is not None
    assert run.draft.id == draft.id


# ---------------------------------------------------------------
# TEST 5: Empty employee_data is valid
# ---------------------------------------------------------------
def test_draft_empty_data(ctx):
    """An empty list is valid (edge case: CSV with headers but no rows)."""
    _company, run = _create_company_and_run()

    draft = PayrollDraft(payroll_run_id=run.id, company_id=run.company_id, employee_data=[])
    db.session.add(draft)
    db.session.commit()

    retrieved = PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).first()
    assert retrieved.employee_data == []


# ---------------------------------------------------------------
# TEST 6: Large dataset doesn't break
# ---------------------------------------------------------------
def test_draft_large_dataset(ctx):
    """100 employees should store and retrieve without issues."""
    _company, run = _create_company_and_run()

    large_data = []
    for i in range(100):
        large_data.append(
            {
                'id': f'EMP{i:03d}',
                'name': f'Employee {i}',
                'basic': 5000 + i * 100,
                'allowances': 1000,
                'gross': 6000 + i * 100,
                'taxable': 5580 + i * 100,
                'tax': 500,
                'pension_employee': 350 + i * 7,
                'pension_employer': 550 + i * 11,
                'net': 5000 + i * 100,
                'bank': 'cash',
            }
        )

    draft = PayrollDraft(payroll_run_id=run.id, company_id=run.company_id, employee_data=large_data)
    db.session.add(draft)
    db.session.commit()

    retrieved = PayrollDraft.query.filter_by(payroll_run_id=run.id, company_id=run.company_id).first()
    assert len(retrieved.employee_data) == 100
    assert retrieved.employee_data[99]['id'] == 'EMP099'
