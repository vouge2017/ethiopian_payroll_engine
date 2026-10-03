"""Item 3: the mixed-state guard.

An employee who already has payroll_item_assignment rows AND still has
unconverted legacy rows is in a state the engine cannot interpret safely: the
engine would read the hand-created assignments while the bridge still reads
the legacy rows, so the same money could be counted twice.

The backfill must refuse that COMPANY, name the employees, write nothing, and
still let a clean company in the same run proceed.
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


def _make_company(name, with_mixed):
    from payroll_engine.catalog import seed_company_templates
    from payroll_engine.models import (
        Company,
        Employee,
        EmployeeAllowance,
        User,
    )
    from payroll_engine.models_payroll_elements import (
        PayItemType,
        PayrollItemAssignment,
    )

    co = Company(name=name)
    db.session.add(co)
    db.session.commit()
    seed_company_templates(co.id)
    db.session.commit()
    u = User(phone=f'09110000{co.id:02d}', company_id=co.id, role='owner')
    u.set_password('Test1234!')
    db.session.add(u)

    emp = Employee(
        employee_id='EMP001',
        name=f'{name} Person',
        basic_salary=Decimal('20000'),
        allowances=Decimal('0'),
        company_id=co.id,
        start_date=date(2020, 1, 1),
    )
    db.session.add(emp)
    db.session.commit()

    # Legacy rows in BOTH companies.
    db.session.add(
        EmployeeAllowance(
            company_id=co.id,
            employee_id=emp.id,
            allowance_type='housing',
            amount=Decimal('2000'),
            calculation_basis='fixed',
            tax_treatment='taxable',
            is_active=True,
            effective_date=date(2020, 1, 1),
        )
    )
    db.session.commit()

    if with_mixed:
        # A hand-created assignment (legacy_source is None) alongside the
        # unconverted legacy row: exactly the ambiguous state.
        item = PayItemType.query.filter_by(company_id=co.id, key='transport').first()
        db.session.add(
            PayrollItemAssignment(
                company_id=co.id,
                employee_id=emp.id,
                pay_item_type_id=item.id,
                fixed_amount=Decimal('500'),
                is_active=True,
            )
        )
        db.session.commit()
    return co, emp


def test_mixed_state_aborts_that_company_and_names_the_employee(ctx):
    from payroll_engine.backfill import backfill_company, find_mixed_state
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    co, _emp = _make_company('Mixed', with_mixed=True)

    mixed = find_mixed_state(co.id)
    assert len(mixed) == 1
    assert mixed[0]['name'] == 'Mixed Person'
    assert mixed[0]['assignments'] == 1
    assert mixed[0]['legacy_rows'] == 1

    counts_before = PayrollItemAssignment.query.filter_by(company_id=co.id).count()
    result = backfill_company(co.id)

    assert result['error'], 'the backfill must refuse a mixed-state company'
    assert 'MIXED STATE' in result['error']
    assert 'Mixed Person' in result['error'], f'the error must NAME the employee, got: {result["error"]}'
    assert '1 assignment(s)' in result['error']
    assert '1 unconverted legacy row(s)' in result['error']

    # Atomicity: nothing new written for that company.
    assert PayrollItemAssignment.query.filter_by(company_id=co.id).count() == counts_before
    assert result['basic_created'] == 0
    assert result['allowances_created'] == 0
    assert result['deductions_created'] == 0


def test_clean_company_in_the_same_run_still_backfills(ctx):
    """One bad tenant must not block a good one."""
    from payroll_engine.backfill import backfill_all
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    mixed_co, _ = _make_company('Mixed', with_mixed=True)
    clean_co, _ = _make_company('Clean', with_mixed=False)

    results = backfill_all(dry_run=False)
    by_id = {r['company_id']: r for r in results}

    assert by_id[mixed_co.id].get('error'), 'the mixed company must abort'
    assert 'Mixed Person' in by_id[mixed_co.id]['error']

    clean = by_id[clean_co.id]
    assert not clean.get('error'), f'the clean company must succeed: {clean}'
    assert clean['basic_created'] == 1
    assert clean['allowances_created'] == 1

    # The clean company really has its rows.
    assert PayrollItemAssignment.query.filter_by(company_id=clean_co.id).count() == 2
    # The mixed company has only its pre-existing hand-created row.
    assert PayrollItemAssignment.query.filter_by(company_id=mixed_co.id).count() == 1
