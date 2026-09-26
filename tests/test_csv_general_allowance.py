"""Consumer 7: the legacy (basic_salary, allowances) CSV keeps working.

The CSV import format has a single undifferentiated `allowances` column. Under
the elements model gross is assembled from assignments, so that bare number
would silently disappear from the payslip. These tests prove it is carried
across as a General Allowance assignment instead.

No itemised CSV columns in this phase -- that is a later change.
"""
from decimal import Decimal
from datetime import date

import pytest
from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, PayrollDraft, PayrollRun, User


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
def company(ctx):
    from payroll_engine.catalog import seed_company_templates

    co = Company(name='CsvCo')
    db.session.add(co)
    db.session.commit()
    seed_company_templates(co.id)
    db.session.commit()
    return co


def _draft_row(**over):
    row = {
        'id': 'EMP001', 'name': 'Dawit', 'basic': 10000.0, 'allowances': 2500.0,
        'gross': 12500.0, 'tax': 1500.0, 'pension_employee': 700.0,
        'pension_employer': 1100.0, 'net': 10300.0,
    }
    row.update(over)
    return row


def test_annotate_marks_allowances_and_seeds_item(company):
    """The upload path stamps general_allowance and guarantees the item exists."""
    from payroll_engine.constants import COMPANY_TEMPLATE_ITEM_KEYS
    from payroll_engine.models_payroll_elements import PayItemType
    from payroll_engine.payroll_bp import _annotate_general_allowance

    rows = [_draft_row(), _draft_row(id='EMP002', allowances=0)]
    n = _annotate_general_allowance(company.id, rows)

    assert n == 1, 'only the row with a positive allowance is marked'
    assert rows[0]['general_allowance'] == 2500.0
    assert rows[1]['general_allowance'] is None

    item = PayItemType.query.filter_by(
        company_id=company.id,
        key=COMPANY_TEMPLATE_ITEM_KEYS.GENERAL_ALLOWANCE.value,
    ).first()
    assert item is not None, 'the General Allowance item must exist for the company'
    assert item.classification == 'earning'


def test_csv_allowance_becomes_assignment_and_reaches_gross(ctx, company):
    """End to end: annotated draft row -> assignment -> gross includes it."""
    from payroll_engine.constants import COMPANY_TEMPLATE_ITEM_KEYS
    from payroll_engine.models import Payslip
    from payroll_engine.models_payroll_elements import PayrollItemAssignment
    from payroll_engine.payroll_bp import _annotate_general_allowance
    from payroll_engine.services.payroll_service import process_payroll

    user = User(phone='0911000001', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()

    rows = [_draft_row()]
    _annotate_general_allowance(company.id, rows)

    run = PayrollRun(
        company_id=company.id, period='2026-09', status='review',
        run_date=date(2026, 9, 1), approved_by=user.id,
    )
    db.session.add(run)
    db.session.commit()
    db.session.add(
        PayrollDraft(payroll_run_id=run.id, company_id=company.id, employee_data=rows)
    )
    db.session.commit()

    result = process_payroll(
        run=run, company_id=company.id, user_id=user.id,
        user_email=user.email or 'owner@test.com', request_ip='127.0.0.1',
    )
    assert result.success is True

    emp = Employee.query.filter_by(company_id=company.id, employee_id='EMP001').first()
    assert emp is not None

    ga = PayrollItemAssignment.query.filter_by(
        company_id=company.id,
        employee_id=emp.id,
        pay_item_type_id=_ga_item(company.id).id,
    ).first()
    assert ga is not None, 'CSV allowance must become a General Allowance assignment'
    assert ga.fixed_amount == Decimal('2500')

    payslip = Payslip.query.filter_by(
        payroll_run_id=run.id, company_id=company.id
    ).first()
    assert payslip is not None
    # 10000 basic + 2500 general allowance
    assert payslip.gross_salary == Decimal('12500'), (
        f"CSV allowances must reach gross, got {payslip.gross_salary}"
    )
    keys = {li['item_key'] for li in (payslip.line_items or [])}
    assert COMPANY_TEMPLATE_ITEM_KEYS.GENERAL_ALLOWANCE.value in keys


def _ga_item(company_id):
    from payroll_engine.constants import COMPANY_TEMPLATE_ITEM_KEYS
    from payroll_engine.models_payroll_elements import PayItemType

    return PayItemType.query.filter_by(
        company_id=company_id,
        key=COMPANY_TEMPLATE_ITEM_KEYS.GENERAL_ALLOWANCE.value,
    ).first()


def test_zero_allowance_creates_no_assignment(ctx, company):
    """A row with no allowances must not get a pointless assignment."""
    from payroll_engine.services.payroll_service import _ensure_general_allowance

    emp = Employee(
        employee_id='EMP002', name='No Allowance',
        basic_salary=10000, company_id=company.id,
    )
    db.session.add(emp)
    db.session.commit()

    assert _ensure_general_allowance(emp, company.id, 0) is None
    assert _ensure_general_allowance(emp, company.id, None) is None


def test_ensure_general_allowance_is_idempotent(ctx, company):
    from payroll_engine.models_payroll_elements import PayrollItemAssignment
    from payroll_engine.services.payroll_service import _ensure_general_allowance

    emp = Employee(
        employee_id='EMP003', name='Idem',
        basic_salary=10000, company_id=company.id,
    )
    db.session.add(emp)
    db.session.commit()

    first = _ensure_general_allowance(emp, company.id, 2500)
    second = _ensure_general_allowance(emp, company.id, 9999)

    assert first is not None and second is not None
    assert first.id == second.id, 'must not create a second assignment'
    assert first.fixed_amount == Decimal('2500'), 'original amount preserved'
    count = PayrollItemAssignment.query.filter_by(
        company_id=company.id, employee_id=emp.id
    ).count()
    assert count == 1


# ---------------------------------------------------------------------------
# 1b. Edge case: no basic salary must NOT synthesise pay.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('amount', [None, 0, Decimal('0'), Decimal('0.00')])
def test_no_basic_salary_creates_no_basic_assignment(ctx, company, amount):
    """A zero/None basic salary must never become a fabricated assignment.

    _ensure_basic_assignment is on the money path, so an absent salary has to
    produce no row at all rather than a 0.00 assignment that could later be
    mistaken for a real figure.

    Employee.basic_salary is NOT NULL in the schema, so a persisted employee
    always has some value; the falsy inputs are exercised against the helper's
    contract (draft rows can carry None, and a 0 basic is legal for e.g. an
    apprentice or a part-period joiner).
    """
    from payroll_engine.models_payroll_elements import PayrollItemAssignment
    from payroll_engine.services.payroll_service import _ensure_basic_assignment

    emp = Employee(
        employee_id='EMP-NOBASIC', name='No Basic',
        basic_salary=0, company_id=company.id,
    )
    db.session.add(emp)
    db.session.commit()

    before = PayrollItemAssignment.query.filter_by(
        company_id=company.id, employee_id=emp.id
    ).count()

    assert _ensure_basic_assignment(emp, company.id, amount) is None

    after = PayrollItemAssignment.query.filter_by(
        company_id=company.id, employee_id=emp.id
    ).count()
    assert after == before, 'no assignment may be created for a zero basic salary'


def test_employee_with_only_non_basic_assignment_gets_full_basic(ctx, company):
    """Generalised invariant: engine path => basic salary is in gross.

    Consumer 2 left this unproven. Gross is assembled entirely from assignments,
    so an employee holding only a non-basic row (here General Allowance) is paid
    2,500 instead of 12,500. This locks the fix at the level of the invariant,
    not the CSV path that happened to expose it.
    """
    from payroll_engine.constants import COMPANY_TEMPLATE_ITEM_KEYS
    from payroll_engine.models import Payslip
    from payroll_engine.models_payroll_elements import PayrollItemAssignment
    from payroll_engine.services.payroll_service import process_payroll

    user = User(phone='0911000001', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    db.session.commit()

    run = PayrollRun(
        company_id=company.id, period='2026-09', status='review',
        run_date=date(2026, 9, 1), approved_by=user.id,
    )
    db.session.add(run)
    db.session.commit()

    # Draft row carrying ONLY a general allowance -- no basic assignment exists
    # for this employee, which is exactly the underpayment condition.
    row = _draft_row()
    row['general_allowance'] = 2500.0
    db.session.add(
        PayrollDraft(payroll_run_id=run.id, company_id=company.id, employee_data=[row])
    )
    db.session.commit()

    result = process_payroll(
        run=run, company_id=company.id, user_id=user.id,
        user_email=user.email or 'owner@test.com', request_ip='127.0.0.1',
    )
    assert result.success is True

    payslip = Payslip.query.filter_by(
        payroll_run_id=run.id, company_id=company.id
    ).first()
    assert payslip is not None
    assert payslip.gross_salary == Decimal('12500'), (
        f"engine path must include the employee's full basic salary, got "
        f"{payslip.gross_salary}"
    )

    keys = {li['item_key'] for li in (payslip.line_items or [])}
    assert 'basic_salary' in keys, (
        'a basic_salary line must be present on the engine path'
    )
    assert COMPANY_TEMPLATE_ITEM_KEYS.GENERAL_ALLOWANCE.value in keys

    emp = Employee.query.filter_by(
        company_id=company.id, employee_id='EMP001'
    ).first()
    basic_assignments = [
        a for a in PayrollItemAssignment.query.filter_by(
            company_id=company.id, employee_id=emp.id, is_active=True
        ).all()
        if a.item_type and a.item_type.key == 'basic_salary'
    ]
    assert len(basic_assignments) == 1
    assert basic_assignments[0].fixed_amount == Decimal('10000')
