"""
Leave balance tests — verifies no double-counting when approving
multiple leave requests in sequence.

The single source of truth is the Leave table (status='approved').
balance.taken is always derived from the DB sum, never manually incremented.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User, Employee, Leave, LeaveBalance
from payroll_engine.services.leave_service import (
    request_leave, approve_leave, get_leave_balance, get_or_create_balance
)
from payroll_engine.leave import LeaveType


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


def _create_employee():
    """Create a company and employee with 20 days annual leave entitlement."""
    company = Company(name='LeaveTestCo')
    db.session.add(company)
    db.session.flush()

    user = User(email='hr@leavetest.com', role='owner', company_id=company.id)
    user.set_password('TestPass1!')
    db.session.add(user)
    db.session.flush()

    # Start date 2 years ago → 14 + 2 = 16 days entitled
    emp = Employee(
        employee_id='EMP001', name='Abebe Kebede',
        basic_salary=10000, allowances=2000,
        company_id=company.id,
        start_date=date(2024, 1, 1),
    )
    db.session.add(emp)
    db.session.flush()

    # Pre-create annual leave balance with entitled days
    # last_accrual_date must be set so accrue_annual_leave doesn't recalculate
    balance = LeaveBalance(
        company_id=company.id,
        employee_id=emp.id,
        leave_type=LeaveType.ANNUAL,
        year=2026,
        entitled=16,
        taken=0,
        last_accrual_date=date(2026, 1, 1),
    )
    db.session.add(balance)
    db.session.commit()

    return company, user, emp


def test_approve_two_leaves_sequentially(ctx):
    """Approve two leave requests in sequence — balance must be correct after each."""
    company, user, emp = _create_employee()

    # Request 1: 5 days
    result1 = request_leave(
        employee=emp, company_id=company.id,
        leave_type=LeaveType.ANNUAL,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
        reason='Family visit',
        db_session=db.session,
    )
    assert result1['success'], f"Request 1 failed: {result1['errors']}"
    leave1 = result1['leave']

    # Request 2: 3 days
    result2 = request_leave(
        employee=emp, company_id=company.id,
        leave_type=LeaveType.ANNUAL,
        start_date=date(2026, 9, 1), end_date=date(2026, 9, 3),
        reason='Personal',
        db_session=db.session,
    )
    assert result2['success'], f"Request 2 failed: {result2['errors']}"
    leave2 = result2['leave']

    # Approve leave 1
    approval1 = approve_leave(leave1, approved_by=user.id, db_session=db.session)
    assert approval1['success'], f"Approval 1 failed: {approval1['message']}"

    # Check balance after first approval
    balance1 = get_leave_balance(emp, company.id, LeaveType.ANNUAL, 2026, db.session)
    assert balance1['taken'] == 5, f"After approving 5-day leave: expected taken=5, got {balance1['taken']}"
    assert balance1['remaining'] == 11, f"After approving 5-day leave: expected remaining=11, got {balance1['remaining']}"

    # Approve leave 2
    approval2 = approve_leave(leave2, approved_by=user.id, db_session=db.session)
    assert approval2['success'], f"Approval 2 failed: {approval2['message']}"

    # Check balance after second approval — this is where double-counting would show
    balance2 = get_leave_balance(emp, company.id, LeaveType.ANNUAL, 2026, db.session)
    assert balance2['taken'] == 8, f"After approving both: expected taken=8, got {balance2['taken']}"
    assert balance2['remaining'] == 8, f"After approving both: expected remaining=8, got {balance2['remaining']}"


def test_approve_sick_leave_no_double_count(ctx):
    """Sick leave balance must also derive from Leave table, not cached counter."""
    company, user, emp = _create_employee()

    # Request 10 days sick leave
    result = request_leave(
        employee=emp, company_id=company.id,
        leave_type=LeaveType.SICK,
        start_date=date(2026, 3, 1), end_date=date(2026, 3, 10),
        reason='Flu',
        db_session=db.session,
    )
    assert result['success'], f"Sick request failed: {result['errors']}"
    sick_leave = result['leave']

    # Approve
    approval = approve_leave(sick_leave, approved_by=user.id, db_session=db.session)
    assert approval['success']

    # Balance should reflect 10 days from DB, not cached increment
    balance = get_leave_balance(emp, company.id, LeaveType.SICK, 2026, db.session)
    assert balance['taken'] == 10, f"Expected sick taken=10, got {balance['taken']}"
    assert balance['remaining'] == 170, f"Expected sick remaining=170, got {balance['remaining']}"


def test_rejected_leave_not_counted(ctx):
    """Rejected leaves must not appear in balance."""
    company, user, emp = _create_employee()

    # Request and reject
    result = request_leave(
        employee=emp, company_id=company.id,
        leave_type=LeaveType.ANNUAL,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
        reason='Vacation',
        db_session=db.session,
    )
    assert result['success']
    leave = result['leave']

    # Reject (directly set status — reject_leave requires reason)
    leave.status = 'rejected'
    leave.rejection_reason = 'Too busy'
    db.session.commit()

    # Balance should be 0 taken
    balance = get_leave_balance(emp, company.id, LeaveType.ANNUAL, 2026, db.session)
    assert balance['taken'] == 0, f"Rejected leave counted: taken={balance['taken']}"


def test_pending_leave_not_counted(ctx):
    """Pending (not yet approved) leaves must not appear in balance."""
    company, user, emp = _create_employee()

    # Request but don't approve
    result = request_leave(
        employee=emp, company_id=company.id,
        leave_type=LeaveType.ANNUAL,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
        reason='Maybe vacation',
        db_session=db.session,
    )
    assert result['success']

    # Balance should be 0 taken (pending != approved)
    balance = get_leave_balance(emp, company.id, LeaveType.ANNUAL, 2026, db.session)
    assert balance['taken'] == 0, f"Pending leave counted: taken={balance['taken']}"
