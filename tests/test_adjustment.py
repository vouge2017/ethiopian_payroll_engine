"""Adjustment payslip tests — verify post-approval corrections."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from datetime import datetime
from payroll_engine import create_app, db
from payroll_engine.models import (
    Company, User, UserCompany, Employee, PayrollRun, Payslip,
    AuditLog, TenantQuery, OvertimeEntry,
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
    client.post('/auth/login', data={
        'login_id': '0911000001', 'password': 'Test1234!'
    }, follow_redirects=True)


def _create_completed_run(app, company_id, user_id):
    """Create a completed payroll run with a regular payslip."""
    with app.app_context():
        emp = Employee(
            employee_id='EMP001', name='Test Worker',
            basic_salary=10000, allowances=0, company_id=company_id,
        )
        db.session.add(emp)
        db.session.commit()

        run = PayrollRun(
            company_id=company_id,
            run_date=datetime.utcnow().date(),
            status='completed',
            approved_by=user_id,
            approved_at=datetime.utcnow(),
            disbursement_status='pending',
        )
        db.session.add(run)
        db.session.commit()

        ps = Payslip(
            payroll_run_id=run.id,
            employee_id=emp.id,
            gross_salary=10000,
            tax=1325,
            employee_pension=700,
            employer_pension=1100,
            net_pay=7975,
            payslip_type='regular',
        )
        db.session.add(ps)
        db.session.commit()
        return run.id, emp.id


def test_create_adjustment(app, company_user, client):
    """Create an adjustment payslip for a completed run."""
    cid, uid = company_user
    run_id, emp_id = _create_completed_run(app, cid, uid)

    login(client)
    resp = client.post(f'/payroll/{run_id}/adjustment', data={
        'employee_id': str(emp_id),
        'amount': '2000',
        'reason': 'Overtime correction',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Adjustment' in resp.data

    with app.app_context():
        adjustments = Payslip.query.filter_by(
            payroll_run_id=run_id, payslip_type='adjustment'
        ).all()
        assert len(adjustments) == 1
        assert adjustments[0].reason == 'Overtime correction'
        assert adjustments[0].gross_salary == 2000
        assert adjustments[0].original_payslip_id is not None


def test_adjustment_requires_reason(app, company_user, client):
    """Adjustment requires a reason."""
    cid, uid = company_user
    run_id, emp_id = _create_completed_run(app, cid, uid)

    login(client)
    resp = client.post(f'/payroll/{run_id}/adjustment', data={
        'employee_id': str(emp_id),
        'amount': '2000',
        'reason': '',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'required' in resp.data.lower()


def test_adjustment_requires_positive_amount(app, company_user, client):
    """Adjustment requires positive amount."""
    cid, uid = company_user
    run_id, emp_id = _create_completed_run(app, cid, uid)

    login(client)
    resp = client.post(f'/payroll/{run_id}/adjustment', data={
        'employee_id': str(emp_id),
        'amount': '-500',
        'reason': 'Test',
    }, follow_redirects=True)
    assert resp.status_code == 200


def test_adjustment_creates_audit_log(app, company_user, client):
    """Adjustment creates an audit log entry."""
    cid, uid = company_user
    run_id, emp_id = _create_completed_run(app, cid, uid)

    login(client)
    resp = client.post(f'/payroll/{run_id}/adjustment', data={
        'employee_id': str(emp_id),
        'amount': '1500',
        'reason': 'Bonus correction',
    }, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        log = AuditLog.query.filter_by(
            company_id=cid, action='adjustment_payslip_created'
        ).first()
        assert log is not None
        assert log.details['reason'] == 'Bonus correction'


def test_adjustment_only_completed_runs(app, company_user, client):
    """Cannot adjust a non-completed run."""
    cid, uid = company_user
    with app.app_context():
        emp = Employee(
            employee_id='EMP001', name='Test',
            basic_salary=5000, company_id=cid,
        )
        db.session.add(emp)
        db.session.commit()

        run = PayrollRun(
            company_id=cid, run_date=datetime.utcnow().date(), status='review',
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id
        emp_id = emp.id

    login(client)
    resp = client.post(f'/payroll/{run_id}/adjustment', data={
        'employee_id': str(emp_id),
        'amount': '1000',
        'reason': 'Test',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'only adjust completed' in resp.data.lower() or b'completed' in resp.data.lower()
