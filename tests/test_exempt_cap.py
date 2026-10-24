"""Regression tests: tax-free transport allowance must be the LOWER of
ETB 2,200 or 25% of basic salary.

Test cases from the bug report:
- basic 5,000 with transport 2,000 -> 1,250 tax-free (25% of basic = 1,250 wins)
- basic 18,000 with transport 3,000 -> 2,200 tax-free (flat cap wins)
"""

import os
import sys
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, EmployeeAllowance, TenantQuery
from payroll_engine.payroll_elements import _apply_exempt_cap
from payroll_engine.services.allowance_service import add_allowance_for_employee, get_exempt_allowances


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(EmployeeAllowance)
        yield app
        db.drop_all()


# --- payroll_elements._apply_exempt_cap ---


def _service_item():
    return SimpleNamespace(exempt_cap_amount=Decimal('2200'), exempt_cap_percent=Decimal('25'))


def test_engine_cap_lower_of_amount_and_percent_low_basic():
    """basic 5,000 + transport 2,000: 25% cap (1,250) beats the 2,200 flat cap."""
    assert _apply_exempt_cap(_service_item(), Decimal('2000'), Decimal('5000')) == Decimal('1250.00')


def test_engine_cap_lower_of_amount_and_percent_high_basic():
    """basic 18,000 + transport 3,000: flat cap 2,200 beats the 25% cap (4,500)."""
    assert _apply_exempt_cap(_service_item(), Decimal('3000'), Decimal('18000')) == Decimal('2200.00')


def test_engine_cap_below_both_caps_passes_through():
    """An allowance under both caps is fully exempt."""
    assert _apply_exempt_cap(_service_item(), Decimal('1500'), Decimal('10000')) == Decimal('1500.00')


def test_engine_cap_very_low_basic_percent_wins():
    """basic 2,000: 25% cap is 500 — kills the 2,200 flat cap so all caps bind."""
    assert _apply_exempt_cap(_service_item(), Decimal('2000'), Decimal('2000')) == Decimal('500.00')


def test_engine_cap_rounding_half_up():
    """basic 3,333.33 * 25% = 833.3325 -> quantizes to 833.33 (ROUND_HALF_UP)."""
    assert _apply_exempt_cap(_service_item(), Decimal('2000'), Decimal('3333.33')) == Decimal('833.33')


def test_engine_cap_percent_only_still_works():
    item = SimpleNamespace(exempt_cap_amount=None, exempt_cap_percent=Decimal('25'))
    assert _apply_exempt_cap(item, Decimal('3000'), Decimal('5000')) == Decimal('1250.00')


def test_engine_cap_amount_only_still_works():
    item = SimpleNamespace(exempt_cap_amount=Decimal('2200'), exempt_cap_percent=None)
    assert _apply_exempt_cap(item, Decimal('3000'), Decimal('18000')) == Decimal('2200.00')


# --- EmployeeAllowance.calculated_exempt_amount ---


def _allowance(basic_salary, amount, cap_amount='2200', cap_percent='25'):
    emp = Employee(employee_id='EMP001', name='X', basic_salary=Decimal(basic_salary))
    a = EmployeeAllowance(
        allowance_type='transport',
        amount=Decimal(amount),
        tax_treatment=EmployeeAllowance.TAX_PARTIAL,
        exempt_cap_amount=Decimal(cap_amount) if cap_amount is not None else None,
        exempt_cap_percent=Decimal(cap_percent) if cap_percent is not None else None,
        exempt_cap_basis='basic_salary',
    )
    a.employee = emp
    return a


def test_model_exempt_low_basic():
    """Model path must match: 25% of 5,000 = 1,250 wins."""
    assert _allowance('5000', '2000').calculated_exempt_amount == Decimal('1250.00')


def test_model_exempt_high_basic():
    """Model path must match: flat 2,200 wins at basic 18,000."""
    assert _allowance('18000', '3000').calculated_exempt_amount == Decimal('2200.00')


def test_model_exempt_amount_only():
    assert _allowance('18000', '3000', cap_percent=None).calculated_exempt_amount == Decimal('2200.00')


def test_model_exempt_percent_only():
    assert _allowance('5000', '3000', cap_amount=None).calculated_exempt_amount == Decimal('1250.00')


# --- allowance_service persists both caps for transport ---


@pytest.fixture
def co_emp(app):
    with app.app_context():
        co = Company(name='CapCo')
        db.session.add(co)
        db.session.flush()
        emp = Employee(employee_id='EMP001', name='Worker', basic_salary=Decimal('5000'), company_id=co.id)
        db.session.add(emp)
        db.session.commit()
        return co.id, emp.id


def test_service_stores_both_transport_caps(app, co_emp):
    from payroll_engine.services.allowance_service import TRANSPORT_EXEMPT_CAP_PERCENT_OF_BASIC

    add_allowance_for_employee(
        db.session.get(Employee, co_emp[1]), co_emp[0], 'transport', Decimal('2000'), db_session=db.session
    )
    db.session.commit()
    a = EmployeeAllowance.query.filter_by(employee_id=co_emp[1], company_id=co_emp[0]).one()
    assert a.tax_treatment == 'partial'
    assert a.exempt_cap_amount == Decimal('2200')
    assert a.exempt_cap_percent == TRANSPORT_EXEMPT_CAP_PERCENT_OF_BASIC == Decimal('25')


def test_service_exempt_low_basic(app, co_emp):
    """Saved record + reloaded employee must give 1,250 for basic 5,000."""
    add_allowance_for_employee(
        db.session.get(Employee, co_emp[1]), co_emp[0], 'transport', Decimal('2000'), db_session=db.session
    )
    db.session.commit()
    emp = db.session.get(Employee, co_emp[1])
    assert get_exempt_allowances(emp) == Decimal('1250.00')


def test_service_exempt_high_basic(app, co_emp):
    add_allowance_for_employee(
        db.session.get(Employee, co_emp[1]), co_emp[0], 'transport', Decimal('2000'), db_session=db.session
    )
    db.session.commit()
    emp = db.session.get(Employee, co_emp[1])
    emp.basic_salary = Decimal('18000')
    db.session.commit()
    assert get_exempt_allowances(emp) == Decimal('2000.00')


def test_service_exempt_2200_when_amount_exceeds_all_caps(app, co_emp):
    add_allowance_for_employee(
        db.session.get(Employee, co_emp[1]), co_emp[0], 'transport', Decimal('3000'), db_session=db.session
    )
    db.session.commit()
    emp = db.session.get(Employee, co_emp[1])
    emp.basic_salary = Decimal('18000')
    db.session.commit()
    assert get_exempt_allowances(emp) == Decimal('2200.00')
