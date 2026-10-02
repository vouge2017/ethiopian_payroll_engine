"""Consumer 6: what-if previews resolve pay items from the catalog.

Covers the two guarantees the elements migration requires of impact.py:
  1. The catalog path is actually taken when a company_id is supplied, and it
     produces engine line_items rather than bare numbers.
  2. A what-if NEVER writes. No EmployeeAllowance, no EmployeeDeduction, and no
     PayrollItemAssignment is persisted by a preview.
"""

from decimal import Decimal

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, EmployeeAllowance


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        # basic_salary and friends live in the SYSTEM catalog (company_id NULL).
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


@pytest.fixture
def seeded_company(ctx):
    """A company with a catalogued 'transport' item that is NOT exempt."""
    from payroll_engine.catalog import seed_company_templates

    company = Company(name='WhatIfCo')
    db.session.add(company)
    db.session.commit()
    seed_company_templates(company.id)
    db.session.commit()
    return company


def test_resolve_pay_item_prefers_company_row(seeded_company):
    from payroll_engine.impact import resolve_pay_item

    item = resolve_pay_item(seeded_company.id, 'transport')
    assert item is not None
    assert item.key == 'transport'


def test_preview_new_hire_uses_catalog_and_writes_nothing(seeded_company):
    """With a company_id the preview goes through the engine, and persists nothing."""
    from payroll_engine.impact import preview_new_hire
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    allowances_before = EmployeeAllowance.query.count()
    assignments_before = PayrollItemAssignment.query.count()

    result = preview_new_hire(
        basic_salary=20000,
        allowances=0,
        transport_allowance=3000,
        employee_name='New Person',
        company_id=seeded_company.id,
    )

    assert result['type'] == 'new_hire'
    assert result['monthly']['basic'] == Decimal('20000')
    # 20000 basic + 3000 transport must be in gross.
    assert result['monthly']['gross'] == Decimal('23000'), (
        f'catalog path should include the transport item, got {result["monthly"]["gross"]}'
    )

    # The critical guarantee: a preview writes nothing.
    assert EmployeeAllowance.query.count() == allowances_before, 'what-if must never create an EmployeeAllowance'
    assert PayrollItemAssignment.query.count() == assignments_before, (
        'what-if must never persist a PayrollItemAssignment'
    )


def test_preview_allowance_change_uses_catalog(seeded_company):
    from payroll_engine.impact import preview_allowance_change

    result = preview_allowance_change(
        current_amount=2000,
        new_amount=5000,
        basic_salary=20000,
        allowance_type='transport',
        company_id=seeded_company.id,
    )

    assert result['type'] == 'allowance_change'
    assert result['impact']['amount_change'] == Decimal('3000')
    # The engine computed both sides, so both full results are present.
    assert 'current' in result and 'new' in result
    assert result['new']['gross'] > result['current']['gross']


def test_preview_falls_back_when_item_not_in_catalog(seeded_company):
    """An undefined item falls back to legacy math rather than inventing a rule."""
    from payroll_engine.impact import preview_new_hire, resolve_pay_item

    assert resolve_pay_item(seeded_company.id, 'no_such_item_xyz') is None

    # transport_allowance=0 means no item is needed; the plain path must work.
    result = preview_new_hire(
        basic_salary=20000,
        allowances=1000,
        transport_allowance=0,
        company_id=seeded_company.id,
    )
    assert result['monthly']['gross'] == Decimal('21000')


def test_engine_extra_items_are_not_persisted(seeded_company):
    """A transient assignment passed via extra_items must not reach the DB."""
    from datetime import date

    from payroll_engine.impact import _what_if_employee, virtual_assignment
    from payroll_engine.models_payroll_elements import PayrollItemAssignment
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    before = PayrollItemAssignment.query.count()
    basic_va = virtual_assignment(seeded_company.id, 'basic_salary', Decimal('20000'))
    va = virtual_assignment(seeded_company.id, 'transport', Decimal('3000'))
    assert va is not None
    assert va.id is None, 'transient assignment must have no id'
    assert basic_va.id is None

    emp = _what_if_employee(Decimal('20000'), seeded_company.id)
    assert emp.id is None, 'transient employee must have no id'

    result = calculate_payroll_from_assignments(
        emp,
        seeded_company.id,
        date.today(),
        extra_items=[basic_va, va],
    )

    assert result['gross'] == Decimal('23000')
    keys = [li['item_key'] for li in result['line_items']]
    assert 'transport' in keys
    assert 'basic_salary' in keys
    db.session.rollback()
    assert PayrollItemAssignment.query.count() == before


# ---------------------------------------------------------------------------
# Review finding #6: rate_x_units what-if must carry units_field
# ---------------------------------------------------------------------------


def test_preview_new_hire_rate_x_units_with_units(seeded_company):
    """Lock-in 4 proof: the engine must resolve units via
    assignment.units_field and compute rate × units, not rate × 0.

    Quote from payroll_engine/payroll_elements.py::_item_quantity:
      1. If assignment.units_field is set, look up units_input[assignment.units_field].
      2. Otherwise, look up units_input[item.key].
      3. If neither is present, the quantity is 0 (no units this period).
    """
    from payroll_engine import db
    from payroll_engine.impact import virtual_assignment
    from payroll_engine.models_payroll_elements import (
        PayItemType,
    )
    from payroll_engine.payroll_elements import (
        calculate_payroll_from_assignments,
    )

    # Create a temporary rate_x_units item in the catalog.
    # Note: units_field lives on PayrollItemAssignment (lock-in 4),
    # not on PayItemType — do NOT set it here.
    item = PayItemType(
        company_id=seeded_company.id,
        key='test_rate_item',
        name_en='Test Rate Item',
        name_am='ዋና መጠን',
        classification='earning',
        calculation_method='rate_x_units',
        rate=Decimal('150'),
        is_system=False,
        is_active=True,
    )
    db.session.add(item)
    db.session.flush()

    # virtual_assignment must carry units_field so the engine
    # can resolve the quantity from units_input.
    va = virtual_assignment(
        seeded_company.id,
        'test_rate_item',
        Decimal('150'),
        classification='earning',
        units_field='hours',
    )
    assert va is not None
    assert va.units_field == 'hours', (
        'virtual_assignment must persist units_field for the engine to resolve the quantity'
    )

    # Create a transient employee and run the engine with units_input.
    from payroll_engine.impact import _what_if_employee

    emp = _what_if_employee(Decimal('10000'), seeded_company.id)

    result = calculate_payroll_from_assignments(
        emp,
        seeded_company.id,
        __import__('datetime').date.today(),
        extra_items=[va],
        units_input={'hours': 16},
    )

    # 150 × 16 = 2400 must appear in gross.
    gross = result['gross']
    assert gross >= Decimal('2400'), (
        f'rate_x_units must compute 150×16=2400 in gross; got {gross}. units_field must be resolved by the engine'
    )
