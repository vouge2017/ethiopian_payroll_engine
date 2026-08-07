"""Undo approval tests — verify 1-hour window and safety checks."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from datetime import UTC, datetime, timedelta

from payroll_engine import create_app, db
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    OvertimeEntry,
    PayrollRun,
    Payslip,
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


def _create_completed_run(app, company_id, user_id, approved_minutes_ago=30):
    """Create a completed payroll run with payslips."""
    with app.app_context():
        run = PayrollRun(
            company_id=company_id,
            run_date=datetime.now(UTC).date(),
            status='completed',
            approved_by=user_id,
            approved_at=datetime.now(UTC) - timedelta(minutes=approved_minutes_ago),
            disbursement_status='pending',
        )
        db.session.add(run)
        db.session.commit()

        ps = Payslip(
            payroll_run_id=run.id,
            employee_id=1,  # doesn't need to exist for this test
            gross_salary=10000,
            tax=1000,
            employee_pension=700,
            employer_pension=1100,
            net_pay=8300,
        )
        db.session.add(ps)
        db.session.commit()
        return run.id


def test_undo_within_1_hour(app, company_user, client):
    """Can undo approval within 1 hour."""
    cid, uid = company_user
    run_id = _create_completed_run(app, cid, uid, approved_minutes_ago=30)

    login(client)
    resp = client.post(f'/payroll/{run_id}/undo-approval', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        run = db.session.get(PayrollRun, run_id)
        assert run.status == 'review'
        assert run.approved_by is None
        assert run.approved_at is None


def test_undo_after_1_hour_blocked(app, company_user, client):
    """Cannot undo approval after 1 hour."""
    cid, uid = company_user
    run_id = _create_completed_run(app, cid, uid, approved_minutes_ago=61)

    login(client)
    resp = client.post(f'/payroll/{run_id}/undo-approval', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Cannot undo' in resp.data or b'1 hour' in resp.data

    with app.app_context():
        run = db.session.get(PayrollRun, run_id)
        assert run.status == 'completed'  # unchanged


def test_undo_blocked_if_disbursed(app, company_user, client):
    """Cannot undo if disbursement has started."""
    cid, uid = company_user
    run_id = _create_completed_run(app, cid, uid, approved_minutes_ago=10)

    with app.app_context():
        run = db.session.get(PayrollRun, run_id)
        run.disbursement_status = 'disbursed'
        db.session.commit()

    login(client)
    resp = client.post(f'/payroll/{run_id}/undo-approval', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Cannot undo' in resp.data or b'disbursement' in resp.data


def test_undo_deletes_payslips(app, company_user, client):
    """Undo deletes associated payslips."""
    cid, uid = company_user
    run_id = _create_completed_run(app, cid, uid, approved_minutes_ago=10)

    login(client)
    resp = client.post(f'/payroll/{run_id}/undo-approval', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        payslips = Payslip.query.filter_by(payroll_run_id=run_id).all()
        assert len(payslips) == 0


def test_undo_creates_audit_log(app, company_user, client):
    """Undo creates an audit log entry."""
    cid, uid = company_user
    run_id = _create_completed_run(app, cid, uid, approved_minutes_ago=10)

    login(client)
    resp = client.post(f'/payroll/{run_id}/undo-approval', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        log = AuditLog.query.filter_by(company_id=cid, action='payroll_approval_undone').first()
        assert log is not None
        assert log.details['run_id'] == run_id


def test_undo_only_completed_runs(app, company_user, client):
    """Cannot undo a non-completed run."""
    cid, _uid = company_user
    with app.app_context():
        run = PayrollRun(
            company_id=cid,
            run_date=datetime.now(UTC).date(),
            status='review',
        )
        db.session.add(run)
        db.session.commit()
        run_id = run.id

    login(client)
    resp = client.post(f'/payroll/{run_id}/undo-approval', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Only completed' in resp.data
