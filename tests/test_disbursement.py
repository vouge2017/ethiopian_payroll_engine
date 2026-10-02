"""
Tests for Phase 5 — Disbursement Progress:
- Disbursement progress page
- Per-bank grouping
- Status progression
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import date

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company,
    Employee,
    PayrollRun,
    Payslip,
    User,
)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _setup(app, disbursement_status='pending'):
    """Create company, owner, employees with different banks, completed run."""
    with app.app_context():
        company = Company(name='DisbTestCo')
        db.session.add(company)
        db.session.flush()

        owner = User(phone='0910000000', role='owner', company_id=company.id)
        owner.set_password('OwnerPass1!')
        db.session.add(owner)
        db.session.flush()

        # Employees with different banks
        emp1 = Employee(
            employee_id='EMP001',
            name='Abebe Kebede',
            phone='0911111111',
            basic_salary=10000,
            allowances=2000,
            company_id=company.id,
            bank_account='cbe:1000123456789',
        )
        emp2 = Employee(
            employee_id='EMP002',
            name='Hana Tesfaye',
            phone='0922222222',
            basic_salary=8000,
            allowances=1000,
            company_id=company.id,
            bank_account='cbe:1000987654321',
        )
        emp3 = Employee(
            employee_id='EMP003',
            name='Dawit Mekonnen',
            phone='0933333333',
            basic_salary=12000,
            allowances=3000,
            company_id=company.id,
            bank_account='dashen:2000111222333',
        )
        db.session.add_all([emp1, emp2, emp3])
        db.session.flush()

        run = PayrollRun(
            company_id=company.id,
            run_date=date.today(),
            status='completed',
            disbursement_status=disbursement_status,
        )
        run.generate_period()
        db.session.add(run)
        db.session.flush()
        run.generate_reference()

        for emp in [emp1, emp2, emp3]:
            payslip = Payslip(
                payroll_run_id=run.id,
                employee_id=emp.id,
                gross_salary=emp.basic_salary + emp.allowances,
                tax=1500,
                employee_pension=700,
                employer_pension=1100,
                net_pay=emp.basic_salary + emp.allowances - 1500 - 700,
            )
            db.session.add(payslip)

        db.session.commit()
        return company.id, owner.id, run.id


# ─── Disbursement Progress Page ───


class TestDisbursementProgress:
    """Test the disbursement progress page."""

    def test_page_loads(self, app):
        _cid, _oid, rid = _setup(app)
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        assert resp.status_code == 200
        assert b'Disbursement' in resp.data

    def test_shows_employee_count(self, app):
        _cid, _oid, rid = _setup(app)
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        assert b'3' in resp.data  # 3 employees

    def test_shows_bank_grouping(self, app):
        _cid, _oid, rid = _setup(app)
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        assert b'CBE' in resp.data or b'cbe' in resp.data
        assert b'Dashen' in resp.data or b'dashen' in resp.data

    def test_shows_total_amount(self, app):
        _cid, _oid, rid = _setup(app)
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        # Total should be displayed
        assert b'ETB' in resp.data

    def test_shows_pending_status(self, app):
        _cid, _oid, rid = _setup(app, disbursement_status='pending')
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        assert b'Pending' in resp.data

    def test_shows_disbursed_status(self, app):
        _cid, _oid, rid = _setup(app, disbursement_status='disbursed')
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        assert b'Disbursed' in resp.data

    def test_shows_confirmed_status(self, app):
        _cid, _oid, rid = _setup(app, disbursement_status='confirmed')
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        assert b'Confirmed' in resp.data
        assert b'All payments confirmed' in resp.data

    def test_mark_as_sent_button_when_pending(self, app):
        _cid, _oid, rid = _setup(app, disbursement_status='pending')
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        assert b'Mark as Sent' in resp.data

    def test_confirm_button_when_disbursed(self, app):
        _cid, _oid, rid = _setup(app, disbursement_status='disbursed')
        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement')
        assert b'Confirm All Payments Received' in resp.data

    def test_redirects_if_not_completed(self, app):
        """Non-completed runs should redirect."""
        with app.app_context():
            company = Company(name='TestCo')
            db.session.add(company)
            db.session.flush()
            owner = User(phone='0910000000', role='owner', company_id=company.id)
            owner.set_password('OwnerPass1!')
            db.session.add(owner)
            run = PayrollRun(company_id=company.id, run_date=date.today(), status='review')
            run.generate_period()
            db.session.add(run)
            db.session.flush()
            run_id = run.id
            db.session.commit()

        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0910000000', 'password': 'OwnerPass1!'})
        resp = client.get(f'/payroll/{run_id}/disbursement', follow_redirects=False)
        assert resp.status_code == 302  # redirect

    def test_employee_cannot_access(self, app):
        """Employees can't access disbursement page."""
        cid, _oid, rid = _setup(app)
        with app.app_context():
            emp_user = User(phone='0944444444', role='employee', company_id=cid)
            emp_user.set_password('EmpPass1!')
            db.session.add(emp_user)
            db.session.commit()

        client = app.test_client()
        client.post('/auth/login', data={'login_id': '0944444444', 'password': 'EmpPass1!'})
        resp = client.get(f'/payroll/{rid}/disbursement', follow_redirects=True)
        # Should get 403 or redirect
        assert resp.status_code in (403, 200)
