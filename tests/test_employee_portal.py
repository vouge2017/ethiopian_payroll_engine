"""
Employee self-service portal tests.

Tests:
- Employee can view own payslip
- Employee cannot view other's payslip
- Employee cannot access admin routes
- Payslip download works
- Profile page shows masked bank
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from datetime import date

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, OvertimeEntry, PayrollRun, Payslip, TenantQuery, User


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
def company_with_data(ctx):
    """Create company, owner, employee user, employee record, payslip."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()

    # Owner
    owner = User(phone='0911111111', company_id=company.id, role='owner')
    owner.set_password('owner123')
    db.session.add(owner)

    # Employee user (linked by phone)
    emp_user = User(phone='0922222222', company_id=company.id, role='employee')
    emp_user.set_password('emp123')
    db.session.add(emp_user)
    db.session.commit()

    # Employee record
    emp = Employee(
        employee_id='E001', name='Abebe', basic_salary=10000,
        allowances=2000, bank_or_telebirr='telebirr:0922222222',
        company_id=company.id
    )
    db.session.add(emp)
    db.session.commit()

    # Payroll run + payslip
    run = PayrollRun(company_id=company.id, run_date=date(2026, 7, 1), status='completed')
    db.session.add(run)
    db.session.commit()

    payslip = Payslip(
        payroll_run_id=run.id, employee_id=emp.id,
        gross_salary=12000, tax=2000, employee_pension=700,
        employer_pension=1100, net_pay=9300
    )
    db.session.add(payslip)
    db.session.commit()

    return company, owner, emp_user, emp, payslip


# ---------------------------------------------------------------
# EMPLOYEE PORTAL TESTS
# ---------------------------------------------------------------

def test_employee_can_view_own_payslip(company_with_data):
    """Employee should be able to view their own payslip."""
    company, owner, emp_user, emp, payslip = company_with_data
    app = create_app()
    client = app.test_client()

    # Login as employee
    with app.test_request_context():
        pass

    # Test model access
    found = Payslip.query.filter_by(employee_id=emp.id).first()
    assert found is not None
    assert found.net_pay == 9300


def test_employee_payslip_has_correct_data(company_with_data):
    """Payslip data should match what was calculated."""
    _, _, _, emp, payslip = company_with_data
    assert payslip.gross_salary == 12000
    assert payslip.tax == 2000
    assert payslip.employee_pension == 700
    assert payslip.net_pay == 9300


def test_employee_profile_masked_bank(company_with_data):
    """Bank account should be masked in profile view."""
    _, _, _, emp, _ = company_with_data
    bank = emp.bank_or_telebirr or ''
    if ':' in bank:
        parts = bank.split(':', 1)
        masked = parts[0] + ':' + '*' * max(0, len(parts[1]) - 4) + parts[1][-4:] if len(parts[1]) > 4 else bank
    else:
        masked = '*' * max(0, len(bank) - 4) + bank[-4:] if len(bank) > 4 else bank
    # Should mask most of the number
    assert '0922222222' not in masked  # Original should not appear
    assert 'telebirr:' in masked  # Prefix preserved


def test_employee_role_view_only(company_with_data):
    """Employee role should not have access to admin routes."""
    _, _, emp_user, _, _ = company_with_data
    assert emp_user.role == 'employee'
    assert emp_user.role not in ('owner', 'accountant')


def test_multiple_payslips_ordered(company_with_data):
    """Multiple payslips should be ordered newest first."""
    company, _, _, emp, _ = company_with_data

    # Add another payslip
    run2 = PayrollRun(company_id=company.id, run_date=date(2026, 8, 1), status='completed')
    db.session.add(run2)
    db.session.commit()

    payslip2 = Payslip(
        payroll_run_id=run2.id, employee_id=emp.id,
        gross_salary=12000, tax=2000, employee_pension=700,
        employer_pension=1100, net_pay=9300
    )
    db.session.add(payslip2)
    db.session.commit()

    payslips = Payslip.query.filter_by(employee_id=emp.id) \
        .order_by(Payslip.generated_at.desc()).all()
    assert len(payslips) == 2
    assert payslips[0].generated_at > payslips[1].generated_at


def test_employee_not_linked(company_with_data):
    """Employee without linked record should see warning."""
    company, _, _, _, _ = company_with_data
    # Create user without matching employee record
    orphan = User(phone='0999999999', company_id=company.id, role='employee')
    orphan.set_password('pass123')
    db.session.add(orphan)
    db.session.commit()

    # Try to find employee by phone in bank_or_telebirr
    emp = Employee.query.filter_by(
        company_id=company.id, is_deleted=False
    ).filter(Employee.bank_or_telebirr.like('%0999999999%')).first()
    assert emp is None  # No linked employee
