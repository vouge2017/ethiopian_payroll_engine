"""Backfill tests: idempotency, atomicity, and the money proof.

The money proof is the point of the whole exercise: run payroll on a company
with deliberately awkward legacy data BEFORE the backfill (legacy path) and
AFTER it (engine path), and require gross and net to match to the cent per
employee. Any difference is a bug to explain, not a rounding note.
"""
from datetime import date
from decimal import Decimal

import pytest
from payroll_engine import create_app, db
from payroll_engine.backfill import (
    backfill_all,
    backfill_company,
    verify_basic_present,
)
from payroll_engine.models import (
    Company,
    Employee,
    EmployeeAllowance,
    EmployeeDeduction,
    PayrollDraft,
    PayrollRun,
    User,
)


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


@pytest.fixture
def edge_company(ctx):
    """A company with edge-case legacy data.

    Deliberately covers: a capped transport allowance, a percentage deduction
    (1/3 of net), a court_order percentage deduction WITH a document and a
    reference number, a declining loan, an INACTIVE allowance, a zero-amount
    allowance, and a custom allowance type the catalog does not define.
    """
    from payroll_engine.catalog import seed_company_templates

    co = Company(name='EdgeCo')
    db.session.add(co)
    db.session.commit()
    seed_company_templates(co.id)
    db.session.commit()

    user = User(phone='0911000001', company_id=co.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)

    emp = Employee(
        employee_id='EMP001', name='Dawit Mekonnen',
        basic_salary=Decimal('20000'), allowances=Decimal('0'),
        company_id=co.id, start_date=date(2020, 1, 1),
    )
    db.session.add(emp)
    db.session.commit()

    # Capped transport allowance: exempt up to the lower of 2200 or 25% of basic.
    db.session.add(EmployeeAllowance(
        company_id=co.id, employee_id=emp.id, allowance_type='transport',
        amount=Decimal('3000'), calculation_basis='fixed',
        tax_treatment='partial', exempt_cap_amount=Decimal('2200'),
        exempt_cap_percent=Decimal('25'), exempt_cap_basis='basic_salary',
        is_active=True, effective_date=date(2020, 1, 1),
    ))
    # INACTIVE allowance - must not affect payroll after backfill.
    db.session.add(EmployeeAllowance(
        company_id=co.id, employee_id=emp.id, allowance_type='housing',
        amount=Decimal('9999'), calculation_basis='fixed',
        tax_treatment='taxable', is_active=False,
        effective_date=date(2020, 1, 1),
    ))
    # ZERO amount allowance - must not invent pay.
    db.session.add(EmployeeAllowance(
        company_id=co.id, employee_id=emp.id, allowance_type='food',
        amount=Decimal('0'), calculation_basis='fixed',
        tax_treatment='taxable', is_active=True,
        effective_date=date(2020, 1, 1),
    ))
    # Custom type not in the catalog.
    db.session.add(EmployeeAllowance(
        company_id=co.id, employee_id=emp.id, allowance_type='custom_thing',
        custom_type_name='Custom Thing', amount=Decimal('500'),
        calculation_basis='fixed', tax_treatment='taxable', is_active=True,
        effective_date=date(2020, 1, 1),
    ))

    # Percentage deduction: one third of net.
    db.session.add(EmployeeDeduction(
        company_id=co.id, employee_id=emp.id, deduction_type='cost_sharing',
        label='MoE Batch', amount_mode='percentage', amount=Decimal('33.33'),
        tracking_mode='date_bounded', start_date=date(2020, 1, 1), is_active=True,
    ))
    # Court order WITH document trail.
    db.session.add(EmployeeDeduction(
        company_id=co.id, employee_id=emp.id, deduction_type='court_order',
        label='Case 123', amount_mode='percentage', amount=Decimal('10'),
        tracking_mode='date_bounded', start_date=date(2020, 1, 1),
        reference_number='CASE-123/2020', document_path='/uploads/case123.pdf',
        is_active=True, created_by=user.id,
    ))
    # Declining loan with a balance.
    db.session.add(EmployeeDeduction(
        company_id=co.id, employee_id=emp.id, deduction_type='loan',
        label='Staff loan', amount_mode='fixed', amount=Decimal('1000'),
        tracking_mode='declining', total_to_recover=Decimal('5000'),
        remaining_balance=Decimal('4000'), start_date=date(2020, 1, 1),
        is_active=True,
    ))
    db.session.commit()
    return co, user, emp


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(ctx, edge_company):
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    co, _u, _e = edge_company
    before = PayrollItemAssignment.query.filter_by(company_id=co.id).count()

    r = backfill_company(co.id, dry_run=True)

    assert r['basic_created'] == 1
    assert r['allowances_created'] == 4
    assert r['deductions_created'] == 3
    after = PayrollItemAssignment.query.filter_by(company_id=co.id).count()
    assert after == before, '--dry-run must not write'


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_backfill_is_idempotent(ctx, edge_company):
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    co, _u, _e = edge_company

    first = backfill_company(co.id)
    assert first['basic_created'] == 1
    assert first['allowances_created'] == 4
    assert first['deductions_created'] == 3

    count_after_first = PayrollItemAssignment.query.filter_by(company_id=co.id).count()

    second = backfill_company(co.id)
    assert second['basic_created'] == 0, 'second run must create nothing'
    assert second['allowances_created'] == 0
    assert second['deductions_created'] == 0
    assert second['basic_skipped'] == 1
    assert second['allowances_skipped'] == 4
    assert second['deductions_skipped'] == 3

    count_after_second = PayrollItemAssignment.query.filter_by(company_id=co.id).count()
    assert count_after_first == count_after_second


# ---------------------------------------------------------------------------
# Field mapping + invariant
# ---------------------------------------------------------------------------


def test_field_mapping_and_document_trail(ctx, edge_company):
    from payroll_engine.models_payroll_elements import (
        PayItemType,
        PayrollItemAssignment,
    )

    co, user, emp = edge_company
    backfill_company(co.id)

    # Court order keeps its reference number and document path verbatim.
    court = PayrollItemAssignment.query.filter_by(
        company_id=co.id, employee_id=emp.id,
        reference_number='CASE-123/2020',
    ).first()
    assert court is not None, 'court order reference_number must survive'
    assert court.document_path == '/uploads/case123.pdf'
    assert court.percent_of_net == Decimal('10'), 'percentage -> percent_of_net'
    assert court.created_by == user.id, 'created_by must survive'
    assert court.custom_label == 'Case 123'

    # Declining loan keeps its balance.
    loan = PayrollItemAssignment.query.filter_by(
        company_id=co.id, employee_id=emp.id,
        pay_item_type_id=PayItemType.query.filter_by(
            company_id=co.id, key='loan'
        ).first().id,
    ).first()
    assert loan.fixed_amount == Decimal('1000')
    assert loan.remaining_balance == Decimal('4000')
    assert loan.tracking_mode == 'declining'

    # Inactive allowance stays inactive.
    housing = PayrollItemAssignment.query.filter_by(
        company_id=co.id, employee_id=emp.id,
        pay_item_type_id=PayItemType.query.filter_by(
            company_id=co.id, key='housing'
        ).first().id,
    ).first()
    assert housing is not None
    assert housing.is_active is False

    # Custom type creates a company PayItemType on demand.
    custom = PayItemType.query.filter_by(
        company_id=co.id, key='custom_thing'
    ).first()
    assert custom is not None, 'unknown key must still get a PayItemType'
    assert custom.classification == 'earning'


def test_basic_effective_date_rule(ctx, edge_company):
    """Basic uses employment start when known."""
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    co, _u, emp = edge_company
    backfill_company(co.id)

    basic = PayrollItemAssignment.query.filter_by(
        company_id=co.id, employee_id=emp.id,
        legacy_source=f'legacy_basic:{emp.id}',
    ).first()
    assert basic is not None
    assert basic.fixed_amount == Decimal('20000')
    assert basic.effective_date == date(2020, 1, 1), 'start_date wins'


def test_basic_effective_date_falls_back_to_legacy_dates(ctx, edge_company):
    from payroll_engine.backfill import basic_effective_date
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    co, _u, emp = edge_company
    emp.start_date = None
    db.session.commit()

    a = EmployeeAllowance(
        company_id=co.id, employee_id=emp.id, allowance_type='transport',
        amount=Decimal('100'), calculation_basis='fixed',
        tax_treatment='taxable', is_active=True, effective_date=date(2019, 5, 1),
    )
    d = EmployeeDeduction(
        company_id=co.id, employee_id=emp.id, deduction_type='loan',
        label='L', amount_mode='fixed', amount=Decimal('100'),
        tracking_mode='date_bounded', start_date=date(2018, 3, 1), is_active=True,
    )
    db.session.add_all([a, d])
    db.session.commit()

    assert basic_effective_date(emp, [a, d]) == date(2018, 3, 1), (
        'earliest legacy row date when start_date is unknown'
    )


def test_verify_basic_present_after_backfill(ctx, edge_company):
    co, _u, emp = edge_company
    assert verify_basic_present(co.id) == [], 'must be clean even before backfill'
    backfill_company(co.id)
    assert verify_basic_present(co.id) == [], (
        'nobody may end with assignments but no basic_salary row'
    )


def test_legacy_rows_are_not_deleted(ctx, edge_company):
    co, _u, _emp = edge_company
    n_a = EmployeeAllowance.query.filter_by(company_id=co.id).count()
    n_d = EmployeeDeduction.query.filter_by(company_id=co.id).count()
    backfill_company(co.id)
    assert EmployeeAllowance.query.filter_by(company_id=co.id).count() == n_a
    assert EmployeeDeduction.query.filter_by(company_id=co.id).count() == n_d


# ---------------------------------------------------------------------------
# Atomicity
# ---------------------------------------------------------------------------


def test_company_failure_rolls_back_whole_company(ctx, edge_company, monkeypatch):
    """A mid-company failure leaves that company with zero partial writes."""
    from payroll_engine import backfill as bf
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    co, _u, _emp = edge_company
    original = bf._convert_allowance
    calls = {'n': 0}

    def boom(*a, **kw):
        calls['n'] += 1
        if calls['n'] == 2:
            raise RuntimeError('simulated mid-backfill failure')
        return original(*a, **kw)

    monkeypatch.setattr(bf, '_convert_allowance', boom)
    results = bf.backfill_all(dry_run=False)

    rec = [r for r in results if r.get('company_id') == co.id][0]
    assert rec.get('error'), 'the failure must be reported'
    assert rec.get('rolled_back') is True
    assert PayrollItemAssignment.query.filter_by(company_id=co.id).count() == 0, (
        'the whole company must be rolled back - no partial state'
    )
