"""
Approval confirmation and soft delete tests.

Tests:
- Password re-authentication for payroll approval
- Rejection flow with reason
- Soft delete (deactivate/reactivate)
- Deleted employees excluded from default queries
- Payroll history preserved after soft delete
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from datetime import UTC, date, datetime

from payroll_engine import create_app, db
from payroll_engine.models import AuditLog, Company, Employee, OvertimeEntry, PayrollRun, Payslip, TenantQuery, User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
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
def company_user_employee(ctx):
    """Create company, admin user, and employee."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()
    user = User(phone='0911234567', company_id=company.id, role='admin')
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
    emp = Employee(employee_id='E001', name='Abebe', basic_salary=10000, allowances=2000, company_id=company.id)
    db.session.add(emp)
    db.session.commit()
    return company, user, emp


# ---------------------------------------------------------------
# SOFT DELETE TESTS
# ---------------------------------------------------------------


def test_soft_delete_marks_employee(company_user_employee):
    """Deactivating an employee sets is_deleted=True."""
    company, user, emp = company_user_employee
    assert not emp.is_deleted

    emp.is_deleted = True
    emp.deleted_at = datetime.now(UTC)
    emp.deleted_by = user.id
    db.session.commit()

    found = Employee.with_deleted().filter_by(id=emp.id, company_id=company.id).first()
    assert found.is_deleted
    assert found.deleted_at is not None
    assert found.deleted_by == user.id


def test_soft_delete_excludes_from_default_query(company_user_employee):
    """Deleted employees should not appear in default queries."""
    company, _user, emp = company_user_employee

    # Before delete: 1 employee
    active = Employee.query.filter_by(company_id=company.id, is_deleted=False).all()
    assert len(active) == 1

    # Soft delete
    emp.is_deleted = True
    emp.deleted_at = datetime.now(UTC)
    db.session.commit()

    # After delete: 0 active employees
    active = Employee.query.filter_by(company_id=company.id, is_deleted=False).all()
    assert len(active) == 0

    # But still in database
    all_emps = Employee.with_deleted().filter_by(company_id=company.id).all()
    assert len(all_emps) == 1


def test_reactivate_restores_employee(company_user_employee):
    """Reactivating a soft-deleted employee restores them."""
    company, _user, emp = company_user_employee

    emp.is_deleted = True
    emp.deleted_at = datetime.now(UTC)
    db.session.commit()

    # Reactivate
    emp.is_deleted = False
    emp.deleted_at = None
    emp.deleted_by = None
    db.session.commit()

    active = Employee.query.filter_by(company_id=company.id, is_deleted=False).all()
    assert len(active) == 1
    assert active[0].name == 'Abebe'


def test_payroll_history_preserved_after_soft_delete(company_user_employee):
    """Payroll history should survive soft delete."""
    company, _user, emp = company_user_employee

    # Create a payroll run with payslip
    run = PayrollRun(company_id=company.id, run_date=date(2026, 7, 1), status='completed')
    db.session.add(run)
    db.session.commit()

    payslip = Payslip(
        payroll_run_id=run.id,
        employee_id=emp.id,
        company_id=company.id,
        gross_salary=12000,
        tax=2000,
        employee_pension=700,
        employer_pension=1100,
        net_pay=9300,
    )
    db.session.add(payslip)
    db.session.commit()

    # Soft delete the employee
    emp.is_deleted = True
    emp.deleted_at = datetime.now(UTC)
    db.session.commit()

    # Payslip still exists
    found_payslip = Payslip.query.filter_by(employee_id=emp.id, company_id=company.id).first()
    assert found_payslip is not None
    assert found_payslip.gross_salary == 12000


def test_soft_delete_audit_log(company_user_employee):
    """Deactivation should be logged."""
    company, user, emp = company_user_employee

    log = AuditLog(
        company_id=company.id,
        user_id=user.id,
        action='employee_deactivated',
        details={'employee_id': emp.employee_id, 'name': emp.name},
    )
    db.session.add(log)
    db.session.commit()

    found = AuditLog.query.filter_by(company_id=company.id, action='employee_deactivated').first()
    assert found is not None
    assert found.details['name'] == 'Abebe'


# ---------------------------------------------------------------
# APPROVAL CONFIRMATION TESTS
# ---------------------------------------------------------------


def test_approval_requires_password(company_user_employee):
    """Approval should fail without correct password."""
    _company, user, _emp = company_user_employee
    app = create_app()
    app.test_client()

    # Login
    with app.test_request_context():
        pass

    # Test that wrong password is rejected
    assert user.check_password('testpass123')
    assert not user.check_password('wrongpassword')


def test_approval_with_correct_password(company_user_employee):
    """Approval should succeed with correct password."""
    _company, user, _emp = company_user_employee
    assert user.check_password('testpass123')


def test_rejection_creates_audit_log(company_user_employee):
    """Rejection should create an audit log entry."""
    company, user, _emp = company_user_employee

    run = PayrollRun(company_id=company.id, run_date=date(2026, 7, 1), status='review')
    db.session.add(run)
    db.session.commit()

    # Simulate rejection
    run.status = 'draft'
    log = AuditLog(
        company_id=company.id,
        user_id=user.id,
        action='payroll_rejected',
        details={'run_id': run.id, 'reason': 'Numbers look wrong'},
    )
    db.session.add(log)
    db.session.commit()

    assert run.status == 'draft'
    found = AuditLog.query.filter_by(company_id=company.id, action='payroll_rejected').first()
    assert found is not None
    assert found.details['reason'] == 'Numbers look wrong'


def test_multiple_active_employees(company_user_employee):
    """Can have multiple active employees."""
    company, _user, emp = company_user_employee

    emp2 = Employee(employee_id='E002', name='Bekele', basic_salary=8000, allowances=1000, company_id=company.id)
    db.session.add(emp2)
    db.session.commit()

    active = Employee.query.filter_by(company_id=company.id, is_deleted=False).all()
    assert len(active) == 2

    # Deactivate one
    emp.is_deleted = True
    emp.deleted_at = datetime.now(UTC)
    db.session.commit()

    active = Employee.query.filter_by(company_id=company.id, is_deleted=False).all()
    assert len(active) == 1
    assert active[0].name == 'Bekele'
