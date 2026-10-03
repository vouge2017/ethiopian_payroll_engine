"""Item 2: the method/column mismatch must RAISE, never silently evaluate to 0.

The engine used to switch on item_type.calculation_method, so a
percent_of_net value written onto a 'fixed' type was read by the fixed branch
as fixed_amount (None) and deducted nothing -- an overpayment of ETB 7,112.62
in the money proof. Any future writer (UI, CSV, API) could re-arm the same
bug. These tests pin the guard from both sides:

  * a mismatch resolves to the POPULATED column, not the type's default;
  * a genuinely ambiguous assignment (two value columns) raises.
"""

from datetime import date
from decimal import Decimal

import pytest

from payroll_engine import create_app, db


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        from payroll_engine.catalog import seed_system_items

        seed_system_items()
        yield app
        db.session.remove()


@pytest.fixture
def ctx(app):
    with app.app_context():
        db.session.rollback()
        yield
        db.session.rollback()
        db.session.remove()


def _company():
    from payroll_engine.catalog import seed_company_templates
    from payroll_engine.models import Company, Employee, User

    co = Company(name='GuardCo')
    db.session.add(co)
    db.session.commit()
    seed_company_templates(co.id)
    db.session.commit()
    u = User(phone='0911000001', company_id=co.id, role='owner')
    u.set_password('Test1234!')
    db.session.add(u)
    e = Employee(
        employee_id='EMP001',
        name='Guard',
        basic_salary=Decimal('20000'),
        allowances=Decimal('0'),
        company_id=co.id,
        start_date=date(2020, 1, 1),
    )
    db.session.add(e)
    db.session.commit()
    return co, u, e


def test_percent_of_net_on_fixed_type_deducts_not_zeroes(ctx):
    """The exact money-proof bug: must deduct, not evaluate to zero."""
    from payroll_engine.models_payroll_elements import (
        PayItemType,
        PayrollItemAssignment,
    )
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    co, _u, emp = _company()

    item = PayItemType.query.filter_by(company_id=co.id, key='cost_sharing').first()
    assert item.calculation_method == 'fixed', 'precondition: the template ships as fixed, which is what armed the bug'

    basic = PayItemType.query.filter_by(company_id=None, key='basic_salary').first()
    db.session.add(
        PayrollItemAssignment(
            company_id=co.id,
            employee_id=emp.id,
            pay_item_type_id=basic.id,
            fixed_amount=Decimal('20000'),
            is_active=True,
        )
    )
    # percent_of_net on a 'fixed' type -- the writer mistake.
    db.session.add(
        PayrollItemAssignment(
            company_id=co.id,
            employee_id=emp.id,
            pay_item_type_id=item.id,
            percent_of_net=Decimal('25'),
            is_active=True,
        )
    )
    db.session.commit()

    r = calculate_payroll_from_assignments(emp, co.id, date(2026, 9, 1))

    assert r['total_deductions'] > Decimal('0'), (
        'a percent_of_net assignment on a fixed type deducted '
        f'{r["total_deductions"]} -- the overpayment guard is not working'
    )
    assert len(r['deduction_details']) == 1
    assert r['deduction_details'][0]['type'] == 'cost_sharing'


def test_two_value_columns_raises_loudly(ctx):
    """Ambiguity must be an error, never a guess."""
    from payroll_engine.models_payroll_elements import (
        PayItemType,
        PayrollItemAssignment,
    )
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    co, _u, emp = _company()
    item = PayItemType.query.filter_by(company_id=co.id, key='cost_sharing').first()
    basic = PayItemType.query.filter_by(company_id=None, key='basic_salary').first()

    db.session.add(
        PayrollItemAssignment(
            company_id=co.id,
            employee_id=emp.id,
            pay_item_type_id=basic.id,
            fixed_amount=Decimal('20000'),
            is_active=True,
        )
    )
    db.session.add(
        PayrollItemAssignment(
            company_id=co.id,
            employee_id=emp.id,
            pay_item_type_id=item.id,
            fixed_amount=Decimal('500'),
            percent_of_net=Decimal('25'),
            is_active=True,
        )
    )
    db.session.commit()

    with pytest.raises(ValueError) as exc:
        calculate_payroll_from_assignments(emp, co.id, date(2026, 9, 1))
    msg = str(exc.value)
    assert 'cost_sharing' in msg
    assert 'Exactly one is allowed' in msg


def test_fixed_type_with_fixed_amount_still_uses_fixed(ctx):
    """The guard must not break the normal fixed case."""
    from payroll_engine.models_payroll_elements import (
        PayItemType,
        PayrollItemAssignment,
    )
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    co, _u, emp = _company()
    item = PayItemType.query.filter_by(company_id=co.id, key='loan').first()
    basic = PayItemType.query.filter_by(company_id=None, key='basic_salary').first()

    db.session.add(
        PayrollItemAssignment(
            company_id=co.id,
            employee_id=emp.id,
            pay_item_type_id=basic.id,
            fixed_amount=Decimal('20000'),
            is_active=True,
        )
    )
    db.session.add(
        PayrollItemAssignment(
            company_id=co.id,
            employee_id=emp.id,
            pay_item_type_id=item.id,
            fixed_amount=Decimal('1000'),
            is_active=True,
        )
    )
    db.session.commit()

    r = calculate_payroll_from_assignments(emp, co.id, date(2026, 9, 1))
    assert r['total_deductions'] == Decimal('1000').quantize(Decimal('0.01'))
