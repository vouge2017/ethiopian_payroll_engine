"""Final-settlement edge cases.

Covers how the last working month is prorated (hire-relative days),
pension on the prorated basic share, and the Art. 77 statutory leave
fallback. Derived from the launch-readiness review: pro-rata math is
where payrolls silently go wrong.
"""

from datetime import date
from decimal import Decimal

import pytest

from payroll_engine import create_app, db
from payroll_engine.leave import calculate_annual_entitlement
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    EmployeeAllowance,
    EmployeeDeduction,
    FinalSettlement,
    Leave,
    LeaveBalance,
    OvertimeEntry,
    PayrollRun,
    TenantQuery,
    User,
)
from payroll_engine.pension import employee_pension
from payroll_engine.services.settlement_service import (
    _outstanding_breakdown,
    calculate_outstanding_salary,
    calculate_settlement,
)
from payroll_engine.severance import TerminationReason


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        for model in [
            Employee,
            OvertimeEntry,
            EmployeeDeduction,
            Leave,
            LeaveBalance,
            EmployeeAllowance,
            FinalSettlement,
            PayrollRun,
            AuditLog,
        ]:
            TenantQuery.register_model(model)
        yield app
        db.drop_all()


def _make_company(app):
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.flush()
    user = User(phone='911000001', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    return company


def _make_employee(app, company, start, basic=Decimal('10000'), allowances=Decimal('2000')):
    emp = Employee(
        employee_id='EMP001',
        name='Dawit Mekonnen',
        basic_salary=basic,
        allowances=allowances,
        company_id=company.id,
        start_date=start,
    )
    db.session.add(emp)
    db.session.commit()
    return emp


# --- Outstanding salary proration ---


def test_last_day_feb_full_salary(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 1))
    out = calculate_outstanding_salary(emp, date(2026, 2, 28))
    assert out == Decimal('12000.00')


def test_last_day_leap_feb(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 1))
    out = calculate_outstanding_salary(emp, date(2028, 2, 29))
    assert out == Decimal('12000.00')


def test_last_day_31st_month_full_salary(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 1))
    out = calculate_outstanding_salary(emp, date(2026, 7, 31))
    assert out == Decimal('12000.00')


def test_last_day_december_full_salary(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 1))
    out = calculate_outstanding_salary(emp, date(2026, 12, 31))
    assert out == Decimal('12000.00')


def test_midmonth_counted_from_month_start(app):
    """Terminated on the 15th of the final month → 15/30 of salary."""
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 1))
    breakdown = _outstanding_breakdown(emp, date(2026, 7, 15))
    assert breakdown['days_worked'] == 15
    assert breakdown['total'] == Decimal('6000.00')
    assert breakdown['basic'] == Decimal('5000.00')
    assert breakdown['allowances'] == Decimal('1000.00')


def test_midmonth_hire_counted_from_hire(app):
    """Hired on the 20th of the final month, terminated 26th → 7/30, not 26/30."""
    company = _make_company(app)
    emp = _make_employee(app, company, date(2026, 6, 20))
    breakdown = _outstanding_breakdown(emp, date(2026, 6, 26))
    assert breakdown['days_worked'] == 7
    assert breakdown['total'] == (Decimal('12000') * Decimal(7) / Decimal(30)).quantize(Decimal('0.01'))


def test_midmonth_hire_with_prior_months(app):
    """Employed for years but in the final month only partial: counted from hire day."""
    company = _make_company(app)
    emp = _make_employee(app, company, date(2024, 3, 10))
    breakdown = _outstanding_breakdown(emp, date(2026, 8, 12))
    assert breakdown['days_worked'] == 12


# --- Pension on the prorated basic share ---


def test_settlement_pension_prorated(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2026, 6, 20))
    result = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 6, 26), company.id)
    prorated_basic = (Decimal('10000') * Decimal(7) / Decimal(30)).quantize(Decimal('0.01'))
    assert result['pension_deduction'] == employee_pension(prorated_basic)


def test_settlement_pension_full_month_when_full(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 1))
    result = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 7, 31), company.id)
    assert result['pension_deduction'] == employee_pension(Decimal('10000'))


# --- Leave encashment statutory fallback follows Art. 77 ---


def test_leave_fallback_matches_art77(app):
    """3 years of service → 16 + 1 = 17 days (leave.calculate_annual_entitlement)."""
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 15))
    enc = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 7, 15), company.id)['leave_encashment']
    entitled = calculate_annual_entitlement(3)
    assert entitled == 17
    assert enc == (Decimal('12000') / Decimal('30') * Decimal(17)).quantize(Decimal('0.01'))


def test_leave_fallback_first_year(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2026, 6, 20))
    enc = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 6, 26), company.id)['leave_encashment']
    entitled = calculate_annual_entitlement(0)
    assert entitled == 16
    assert enc == (Decimal('12000') / Decimal('30') * Decimal(16)).quantize(Decimal('0.01'))


def test_leave_balance_record_still_wins(app):
    """A stored LeaveBalance record must override the statutory fallback."""
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 15))
    bal = LeaveBalance(company_id=company.id, employee_id=emp.id, leave_type='annual', year=2026, entitled=18, taken=6)
    db.session.add(bal)
    db.session.commit()
    enc = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 7, 15), company.id, db.session)[
        'leave_encashment'
    ]
    assert enc == (Decimal('12000') / Decimal('30') * Decimal(12)).quantize(Decimal('0.01'))


# --- Settlement date edge: start of month → whole first month ends mid-month


def test_hired_first_of_month_midmonth_term(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2026, 7, 1))
    breakdown = _outstanding_breakdown(emp, date(2026, 7, 15))
    assert breakdown['days_worked'] == 15
    assert breakdown['total'] == Decimal('6000.00')


# --- Determinism of the settlement calculation ---


def test_settlement_deterministic(app):
    company = _make_company(app)
    emp = _make_employee(app, company, date(2023, 1, 15))
    first = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 7, 15), company.id)
    second = calculate_settlement(emp, TerminationReason.REDUNDANCY, date(2026, 7, 15), company.id)
    for key in ('outstanding_salary', 'leave_encashment', 'pension_deduction', 'tax_on_salary', 'net_final_payment'):
        assert first[key] == second[key], f'{key} differs between runs'
