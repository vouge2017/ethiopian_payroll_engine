"""
Employee deduction tests.

Tests:
- Create deduction (fixed, declining balance)
- Create deduction (percentage, date-bounded)
- Stop deduction
- Delete deduction
- Auto-stop when balance exhausted
- Calculate deduction respects remaining balance
- Court order cap validation in validation engine
- Deduction appears in payroll calculation
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import (
    Employee, Company, User, PayrollRun, Payslip,
    AuditLog, TenantQuery, OvertimeEntry, EmployeeDeduction
)
from payroll_engine.payroll import calculate_payroll
from decimal import Decimal
from datetime import date, datetime, timedelta


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
        TenantQuery.register_model(EmployeeDeduction)
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def company_user_employee(ctx):
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()
    user = User(phone='0911000001', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()
    emp = Employee(
        employee_id='EMP001', name='Dawit Mekonnen',
        basic_salary=10000, allowances=2000,
        company_id=company.id
    )
    db.session.add(emp)
    db.session.commit()
    return company, user, emp


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, phone, password):
    return client.post('/auth/login', data={
        'login_id': phone, 'password': password
    }, follow_redirects=True)


# --- Model tests ---

def test_create_fixed_declining_deduction(ctx, company_user_employee):
    """Create a fixed ETB deduction with declining balance."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id,
        employee_id=emp.id,
        deduction_type='cost_sharing',
        label='MoE Batch 2024-07',
        amount_mode='fixed',
        amount=Decimal('500'),
        tracking_mode='declining',
        total_to_recover=Decimal('6000'),
        remaining_balance=Decimal('6000'),
        start_date=date.today(),
        is_active=True,
        created_by=user.id,
    )
    db.session.add(ded)
    db.session.commit()
    assert ded.id is not None
    assert ded.is_active
    assert ded.remaining_balance == Decimal('6000')
    assert ded.type_label == 'Graduate Cost-Sharing'


def test_create_percentage_date_bounded(ctx, company_user_employee):
    """Create a percentage-of-net deduction with date bounds."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id,
        employee_id=emp.id,
        deduction_type='court_order',
        label='Court Case 123/2024',
        amount_mode='percentage',
        amount=Decimal('33.33'),
        tracking_mode='date_bounded',
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        reference_number='CASE-123/2024',
        is_active=True,
        created_by=user.id,
    )
    db.session.add(ded)
    db.session.commit()
    assert ded.amount_mode == 'percentage'
    assert ded.is_date_bounded
    assert not ded.is_expired


def test_calculate_deduction_fixed(ctx, company_user_employee):
    """Fixed deduction returns the fixed amount."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='loan', label='Company Loan',
        amount_mode='fixed', amount=Decimal('1000'),
        tracking_mode='date_bounded',
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    assert ded.calculate_deduction(Decimal('10000')) == Decimal('1000')


def test_calculate_deduction_percentage(ctx, company_user_employee):
    """Percentage deduction calculates correctly."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='court_order', label='Court Order',
        amount_mode='percentage', amount=Decimal('33.33'),
        tracking_mode='date_bounded',
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    # 33.33% of 10000 = 3333
    result = ded.calculate_deduction(Decimal('10000'))
    assert result == Decimal('3333.00')


def test_calculate_deduction_capped_at_balance(ctx, company_user_employee):
    """Declining balance deduction is capped at remaining balance."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='cost_sharing', label='Cost Sharing',
        amount_mode='fixed', amount=Decimal('5000'),
        tracking_mode='declining',
        total_to_recover=Decimal('3000'),
        remaining_balance=Decimal('3000'),
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    # Monthly deduction is 5000, but only 3000 remaining
    assert ded.calculate_deduction(Decimal('10000')) == Decimal('3000')


def test_apply_deduction_decrements_balance(ctx, company_user_employee):
    """Applying a deduction decrements the remaining balance."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='cost_sharing', label='Cost Sharing',
        amount_mode='fixed', amount=Decimal('500'),
        tracking_mode='declining',
        total_to_recover=Decimal('6000'),
        remaining_balance=Decimal('6000'),
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    ded.apply_deduction(Decimal('500'))
    assert ded.remaining_balance == Decimal('5500')
    assert ded.is_active


def test_apply_deduction_auto_stops_at_zero(ctx, company_user_employee):
    """Deduction auto-stops when balance reaches zero."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='cost_sharing', label='Cost Sharing',
        amount_mode='fixed', amount=Decimal('500'),
        tracking_mode='declining',
        total_to_recover=Decimal('500'),
        remaining_balance=Decimal('500'),
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    ded.apply_deduction(Decimal('500'))
    assert ded.remaining_balance == Decimal('0')
    assert not ded.is_active
    assert ded.stopped_reason == 'Balance exhausted'


def test_expired_date_bounded_returns_zero(ctx, company_user_employee):
    """Expired date-bounded deduction returns zero."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='penalty', label='ERCA Penalty',
        amount_mode='fixed', amount=Decimal('1000'),
        tracking_mode='date_bounded',
        start_date=date.today() - timedelta(days=60),
        end_date=date.today() - timedelta(days=1),
        is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    assert ded.is_expired
    assert ded.calculate_deduction(Decimal('10000')) == Decimal('0')


def test_inactive_deduction_returns_zero(ctx, company_user_employee):
    """Inactive deduction returns zero."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='loan', label='Old Loan',
        amount_mode='fixed', amount=Decimal('1000'),
        tracking_mode='date_bounded',
        start_date=date.today(), is_active=False,
    )
    db.session.add(ded)
    db.session.commit()
    assert ded.calculate_deduction(Decimal('10000')) == Decimal('0')


# --- Payroll integration tests ---

def test_payroll_with_deduction(ctx, company_user_employee):
    """Payroll calculation applies post-tax deductions."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='cost_sharing', label='Cost Sharing',
        amount_mode='fixed', amount=Decimal('500'),
        tracking_mode='declining',
        total_to_recover=Decimal('6000'),
        remaining_balance=Decimal('6000'),
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()

    result_without = calculate_payroll(Decimal('10000'), Decimal('2000'))
    result_with = calculate_payroll(Decimal('10000'), Decimal('2000'), deductions=[ded])

    # Net with deduction should be 500 less
    assert result_with['total_deductions'] == Decimal('500.00')
    assert result_with['net'] == result_without['net'] - Decimal('500.00')
    assert result_with['net_before_deductions'] == result_without['net']


def test_payroll_deduction_details(ctx, company_user_employee):
    """Payroll result includes deduction details."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='court_order', label='Court Order',
        amount_mode='fixed', amount=Decimal('1000'),
        tracking_mode='declining',
        total_to_recover=Decimal('5000'),
        remaining_balance=Decimal('5000'),
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()

    result = calculate_payroll(Decimal('10000'), Decimal('2000'), deductions=[ded])
    assert len(result['deduction_details']) == 1
    assert result['deduction_details'][0]['type'] == 'court_order'
    assert result['deduction_details'][0]['amount'] == Decimal('1000')


# --- Route tests ---

def test_add_deduction_route(ctx, client, company_user_employee):
    """POST to add_deduction creates a deduction."""
    company, user, emp = company_user_employee
    login(client, '0911000001', 'Test1234!')

    resp = client.post(f'/employees/{emp.id}/deductions/add', data={
        'deduction_type': 'cost_sharing',
        'label': 'MoE Batch 2024-07',
        'amount_mode': 'fixed',
        'amount': '500',
        'tracking_mode': 'declining',
        'total_to_recover': '6000',
        'start_date': '2026-07-01',
    }, follow_redirects=True)
    assert resp.status_code == 200

    ded = EmployeeDeduction.query.filter_by(company_id=company.id, employee_id=emp.id).first()
    assert ded is not None
    assert ded.label == 'MoE Batch 2024-07'
    assert ded.amount == Decimal('500')
    assert ded.remaining_balance == Decimal('6000')


def test_stop_deduction_route(ctx, client, company_user_employee):
    """POST to stop_deduction deactivates it."""
    company, user, emp = company_user_employee
    login(client, '0911000001', 'Test1234!')

    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='loan', label='Loan',
        amount_mode='fixed', amount=Decimal('500'),
        tracking_mode='date_bounded',
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()

    resp = client.post(f'/deductions/{ded.id}/stop', data={
        'reason': 'Paid in full',
    }, follow_redirects=True)
    assert resp.status_code == 200

    refreshed = db.session.get(EmployeeDeduction, ded.id)
    assert not refreshed.is_active
    assert refreshed.stopped_reason == 'Paid in full'


def test_delete_deduction_route(ctx, client, company_user_employee):
    """POST to delete_deduction removes it (owner only)."""
    company, user, emp = company_user_employee
    login(client, '0911000001', 'Test1234!')

    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='other', label='Test',
        amount_mode='fixed', amount=Decimal('100'),
        tracking_mode='date_bounded',
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    ded_id = ded.id

    resp = client.post(f'/deductions/{ded_id}/delete', follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(EmployeeDeduction, ded_id) is None


# --- Property tests ---

def test_warning_message_low_balance(ctx, company_user_employee):
    """Warning message when balance is less than one monthly deduction."""
    company, user, emp = company_user_employee
    ded = EmployeeDeduction(
        company_id=company.id, employee_id=emp.id,
        deduction_type='cost_sharing', label='Cost Sharing',
        amount_mode='fixed', amount=Decimal('500'),
        tracking_mode='declining',
        total_to_recover=Decimal('6000'),
        remaining_balance=Decimal('300'),  # Less than monthly amount
        start_date=date.today(), is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    warning = ded.warning_message
    assert warning is not None
    assert 'less than one monthly deduction' in warning


def test_type_labels(ctx, company_user_employee):
    """Type labels map correctly."""
    company, user, emp = company_user_employee
    for type_key, expected_label in EmployeeDeduction.DEDUCTION_TYPES:
        ded = EmployeeDeduction(
            company_id=company.id, employee_id=emp.id,
            deduction_type=type_key, label='Test',
            amount_mode='fixed', amount=Decimal('100'),
            tracking_mode='date_bounded',
            start_date=date.today(), is_active=True,
        )
        db.session.add(ded)
        db.session.commit()
        assert ded.type_label == expected_label
        db.session.delete(ded)
        db.session.commit()
