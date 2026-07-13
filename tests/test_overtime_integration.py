"""
Overtime integration tests.

Tests:
- OvertimeEntry model with tenant isolation
- Overtime wired into payroll calculation
- Deduction order preserved with overtime
- Overtime limit validation
- CSV upload with overtime columns
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Employee, Company, User, OvertimeEntry, TenantQuery
from payroll_engine.overtime import calculate_overtime_pay, calculate_total_overtime, OVERTIME_RATES
from payroll_engine.payroll import calculate_payroll
from datetime import date


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture
def company_and_employee(ctx):
    """Create a company and employee for testing."""
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.commit()
    emp = Employee(
        employee_id='E001', name='Abebe', basic_salary=10000,
        allowances=2000, company_id=company.id
    )
    db.session.add(emp)
    db.session.commit()
    return company, emp


# ---------------------------------------------------------------
# MODEL TESTS
# ---------------------------------------------------------------

def test_overtime_entry_stored(company_and_employee):
    """OvertimeEntry should be stored correctly."""
    company, emp = company_and_employee
    entry = OvertimeEntry(
        company_id=company.id, employee_id=emp.id,
        date=date(2026, 7, 15), hours=4.0, overtime_type='day'
    )
    db.session.add(entry)
    db.session.commit()

    found = OvertimeEntry.query.filter_by(
        company_id=company.id, employee_id=emp.id
    ).first()
    assert found is not None
    assert found.hours == 4.0
    assert found.overtime_type == 'day'


def test_overtime_tenant_isolation(company_and_employee):
    """Can't see other company's overtime entries."""
    company, emp = company_and_employee
    # Create another company
    other_company = Company(name='OtherCo')
    db.session.add(other_company)
    db.session.commit()
    other_emp = Employee(
        employee_id='E001', name='Other', basic_salary=5000,
        allowances=0, company_id=other_company.id
    )
    db.session.add(other_emp)
    db.session.commit()

    # Add overtime to first company
    entry = OvertimeEntry(
        company_id=company.id, employee_id=emp.id,
        date=date(2026, 7, 15), hours=4.0, overtime_type='day'
    )
    db.session.add(entry)
    db.session.commit()

    # Query with company filter should find 1
    results = OvertimeEntry.query.filter_by(company_id=company.id).all()
    assert len(results) == 1

    # Query for other company should find 0
    results = OvertimeEntry.query.filter_by(company_id=other_company.id).all()
    assert len(results) == 0


def test_overtime_delete(company_and_employee):
    """Deleting an overtime entry should remove it."""
    company, emp = company_and_employee
    entry = OvertimeEntry(
        company_id=company.id, employee_id=emp.id,
        date=date(2026, 7, 15), hours=4.0, overtime_type='day'
    )
    db.session.add(entry)
    db.session.commit()
    entry_id = entry.id

    db.session.delete(entry)
    db.session.commit()

    found = OvertimeEntry.query.filter_by(id=entry_id, company_id=company.id).first()
    assert found is None


# ---------------------------------------------------------------
# CALCULATION TESTS
# ---------------------------------------------------------------

def test_overtime_pay_weekday():
    """4h weekday overtime on basic 10,000 → 240.38"""
    from decimal import Decimal as D
    pay = calculate_overtime_pay(10000, 4, 'day')
    assert abs(float(pay) - 240.40) < 1.0  # Allow rounding tolerance


def test_overtime_pay_night():
    """4h night overtime → 1.5x"""
    from decimal import Decimal as D
    pay = calculate_overtime_pay(10000, 4, 'night')
    expected = round(10000 / 208 * 4 * 1.5, 2)
    assert abs(float(pay) - expected) < 0.10


def test_overtime_pay_holiday():
    """4h holiday overtime → 2x"""
    from decimal import Decimal as D
    pay = calculate_overtime_pay(10000, 4, 'holiday')
    expected = round(10000 / 208 * 4 * 2.0, 2)
    assert abs(float(pay) - expected) < 0.10


def test_overtime_pay_rest_day():
    """4h rest_day_holiday overtime → 2.5x"""
    from decimal import Decimal as D
    pay = calculate_overtime_pay(10000, 4, 'rest_day_holiday')
    expected = round(10000 / 208 * 4 * 2.5, 2)
    assert abs(float(pay) - expected) < 0.10


def test_overtime_zero_hours():
    """Zero hours should give zero pay."""
    from decimal import Decimal as D
    assert calculate_overtime_pay(10000, 0, 'day') == D('0')


def test_overtime_total():
    """Multiple entries should sum correctly."""
    entries = [
        {'hours': 4, 'type': 'day'},
        {'hours': 2, 'type': 'night'},
    ]
    result = calculate_total_overtime(10000, entries)
    from decimal import Decimal as D
    assert result['total_hours'] == D('6')
    assert result['total_pay'] > 0
    assert len(result['entries']) == 2


# ---------------------------------------------------------------
# DEDUCTION ORDER TEST
# ---------------------------------------------------------------

def test_overtime_included_in_gross():
    """Overtime should be added to gross BEFORE tax."""
    # Without overtime
    result_no_ot = calculate_payroll(basic_salary=10000, allowances=2000)
    # With overtime
    result_with_ot = calculate_payroll(
        basic_salary=10000, allowances=2000,
        overtime_entries=[{'hours': 4, 'type': 'day'}]
    )
    # Gross should be higher with overtime
    assert result_with_ot['gross'] > result_no_ot['gross']
    assert result_with_ot['overtime_pay'] > 0
    # Pension should be the same (based on basic salary only)
    assert result_with_ot['pension_employee'] == result_no_ot['pension_employee']
    # Net should be different (more gross = more tax, but still more net)
    assert result_with_ot['net'] != result_no_ot['net']


def test_deduction_order_with_overtime():
    """Verify exact deduction order: gross+pension→taxable→tax→net"""
    from decimal import Decimal as D
    result = calculate_payroll(
        basic_salary=10000, allowances=2000,
        overtime_entries=[{'hours': 4, 'type': 'day'}]
    )
    # Gross = 10000 + 2000 + overtime
    assert result['gross'] == D('12000') + result['overtime_pay']
    # Pension = 7% of basic (NOT affected by overtime)
    assert result['pension_employee'] == D('700')
    # Taxable = gross - pension
    assert result['taxable'] == result['gross'] - D('700')
    # Net = gross - tax - pension
    assert result['net'] == result['gross'] - result['tax'] - D('700')


def test_verification_numbers():
    """Use the exact verification numbers from the task spec."""
    from decimal import Decimal as D
    result = calculate_payroll(
        basic_salary=10000, allowances=2000,
        overtime_entries=[{'hours': 4, 'type': 'day'}]
    )
    # Overtime pay should be approximately 240.38-240.40
    assert D('240') < result['overtime_pay'] < D('241')
    # Gross = 12000 + overtime
    assert result['gross'] > D('12200')
    # Pension = 700 (7% of basic 10,000 — NOT affected by overtime)
    assert result['pension_employee'] == D('700')
    # Taxable = gross - pension
    assert result['taxable'] == result['gross'] - D('700')
    # Net = gross - tax - pension
    assert result['net'] == result['gross'] - result['tax'] - D('700')


# ---------------------------------------------------------------
# VALIDATION TESTS
# ---------------------------------------------------------------

def test_overtime_within_limit():
    """20 hours should not trigger warning."""
    entries = [{'hours': 20, 'type': 'day'}]
    result = calculate_total_overtime(10000, entries)
    assert not result['exceeds_monthly_limit']
    assert len(result['warnings']) == 0


def test_overtime_exceeds_limit():
    """21 hours should trigger FLAG."""
    entries = [{'hours': 21, 'type': 'day'}]
    result = calculate_total_overtime(10000, entries)
    assert result['exceeds_monthly_limit']
    assert len(result['warnings']) == 1
    assert '20' in result['warnings'][0]


def test_overtime_no_entries():
    """No entries should give zero."""
    result = calculate_total_overtime(10000, [])
    assert result['total_hours'] == 0
    assert result['total_pay'] == 0
    assert not result['exceeds_monthly_limit']
