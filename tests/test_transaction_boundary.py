"""
Transaction boundary tests for payroll approval.

Verifies that the approval flow is atomic: if anything fails midway,
the entire approval rolls back — no partial payslips, no half-committed state.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Company, User, Employee, PayrollRun, Payslip, PayrollDraft,
    AuditLog, PayrollValidationResult,
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


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def _setup_approval_data(app):
    """Create company, user, employee, run, and draft for approval testing."""
    with app.app_context():
        company = Company(name='TestCo')
        db.session.add(company)
        db.session.flush()

        user = User(email='owner@test.com', role='owner', company_id=company.id)
        user.set_password('TestPass1!')
        db.session.add(user)
        db.session.flush()

        emp = Employee(
            employee_id='EMP001', name='Abebe',
            basic_salary=10000, allowances=2000,
            company_id=company.id,
        )
        db.session.add(emp)
        db.session.flush()

        run = PayrollRun(
            company_id=company.id,
            run_date=__import__('datetime').date(2026, 7, 1),
            status='review',
        )
        db.session.add(run)
        db.session.flush()

        draft = PayrollDraft(
            payroll_run_id=run.id,
            employee_data=[{
                'id': 'EMP001',
                'name': 'Abebe',
                'basic': 10000,
                'allowances': 2000,
                'bank': 'dashen:2000987654321',
                'tin': '1234567890',
                'gross': 12000,
                'tax': 1500,
                'pension_employee': 840,
                'pension_employer': 1320,
                'net': 9660,
            }],
        )
        db.session.add(draft)
        db.session.commit()

        return company.id, user.id, run.id


def test_approval_rolls_back_on_pdf_failure(app):
    """
    If PDF generation fails midway through approval, the entire transaction
    must roll back: no payslips, no 'completed' status, no audit log.
    """
    company_id, user_id, run_id = _setup_approval_data(app)

    with app.app_context():
        # Verify starting state
        run = PayrollRun.query.get(run_id)
        assert run.status == 'review'
        assert Payslip.query.filter_by(payroll_run_id=run_id).count() == 0
        assert PayrollDraft.query.filter_by(payroll_run_id=run_id).first() is not None

    # Attempt approval with a failing PDF generator
    with app.test_client() as client:
        with app.app_context():
            user = User.query.get(user_id)
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

        with patch('payroll_engine.payroll_bp.generate_payslip', side_effect=Exception('PDF generation exploded')):
            resp = client.post('/payroll/approve', data={
                'run_id': run_id,
                'password': 'TestPass1!',
            }, follow_redirects=False)

    # After failed approval, verify nothing partial persisted
    with app.app_context():
        run = PayrollRun.query.get(run_id)

        # Run must NOT be 'completed' — rolled back, then marked 'failed'
        assert run.status == 'failed', f"Expected 'failed', got '{run.status}'"

        # No payslips should exist
        payslip_count = Payslip.query.filter_by(payroll_run_id=run_id).count()
        assert payslip_count == 0, f"Expected 0 payslips, got {payslip_count}"

        # Draft should still exist (not cleaned up)
        draft = PayrollDraft.query.filter_by(payroll_run_id=run_id).first()
        assert draft is not None, "Draft was deleted despite rollback"

        # A failure audit log should exist (written in separate transaction)
        fail_log = AuditLog.query.filter_by(
            company_id=company_id, action='payroll_run_failed'
        ).first()
        assert fail_log is not None, "No failure audit log written"
        assert 'PDF generation exploded' in fail_log.details['error']


def test_approval_rolls_back_on_compliance_failure(app):
    """
    If compliance scoring fails after payslips are generated,
    the entire transaction must roll back.
    """
    company_id, user_id, run_id = _setup_approval_data(app)

    with app.test_client() as client:
        with app.app_context():
            user = User.query.get(user_id)
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

        with patch('payroll_engine.payroll_bp.compute_compliance_score', side_effect=Exception('Compliance service down')):
            resp = client.post('/payroll/approve', data={
                'run_id': run_id,
                'password': 'TestPass1!',
            }, follow_redirects=False)

    with app.app_context():
        run = PayrollRun.query.get(run_id)

        # Everything rolled back, then marked 'failed'
        assert run.status == 'failed', f"Expected 'failed', got '{run.status}'"
        assert Payslip.query.filter_by(payroll_run_id=run_id).count() == 0
        assert PayrollDraft.query.filter_by(payroll_run_id=run_id).first() is not None


def test_approval_commits_atomically_on_success(app):
    """
    On successful approval, all changes must persist in a single commit:
    status=completed, payslips, audit log, draft cleanup.
    """
    company_id, user_id, run_id = _setup_approval_data(app)

    with app.test_client() as client:
        with app.app_context():
            user = User.query.get(user_id)
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

        resp = client.post('/payroll/approve', data={
            'run_id': run_id,
            'password': 'TestPass1!',
        }, follow_redirects=False)

    with app.app_context():
        run = PayrollRun.query.get(run_id)

        # All success conditions
        assert run.status == 'completed'
        assert Payslip.query.filter_by(payroll_run_id=run_id).count() == 1
        assert PayrollDraft.query.filter_by(payroll_run_id=run_id).first() is None

        success_log = AuditLog.query.filter_by(
            company_id=company_id, action='payroll_run_completed'
        ).first()
        assert success_log is not None
        assert success_log.details['employee_count'] == 1
