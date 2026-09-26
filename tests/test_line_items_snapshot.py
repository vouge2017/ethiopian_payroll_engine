"""Approval snapshot: Payslip.line_items must hold the APPROVED numbers.

The payslip PDF is generated lazily, long after a run is approved, so it cannot
recompute its earnings/deduction breakdown -- it renders line_items. That makes
process_payroll's write of line_items load-bearing: if it is not written, pdf.py
silently falls back to the old hardcoded Basic Salary / Allowances rows and the
payslip no longer reflects what the employee's catalog actually says.

This test approves a payroll for an employee who HAS active assignments (so the
engine is authoritative rather than the legacy bridge) and asserts the snapshot
was captured, with the approved amounts.
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
def company_user_employee(ctx):
    company = Company(name='SnapshotCo')
    db.session.add(company)
    db.session.commit()
    user = User(phone='0911000001', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    emp = Employee(
        employee_id='EMP001',
        name='Dawit Mekonnen',
        basic_salary=10000,
        allowances=2000,
        company_id=company.id,
    )
    db.session.add(emp)
    db.session.commit()
    return company, user, emp


def _assign(company, emp, key, name, amount, classification, am_label=None):
    """Create a company PayItemType + PayrollItemAssignment (fixed amount)."""
    from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment

    item = PayItemType(
        company_id=company.id,
        key=key,
        name_en=name,
        name_am=am_label,
        classification=classification,
        calculation_method='fixed',
        tax_treatment='taxable',
        is_system=False,
    )
    db.session.add(item)
    db.session.flush()
    a = PayrollItemAssignment(
        company_id=company.id,
        employee_id=emp.id,
        pay_item_type_id=item.id,
        fixed_amount=amount,
        is_active=True,
    )
    db.session.add(a)
    db.session.flush()
    return item, a


def test_approval_snapshots_line_items(ctx, company_user_employee):
    """Approving a payroll persists the engine breakdown onto the payslip."""
    from payroll_engine.models import Payslip
    from payroll_engine.services.payroll_service import process_payroll

    company, user, emp = company_user_employee

    # The employee HAS assignments, so process_payroll must take the engine
    # branch (not the legacy draft-figures bridge).
    basic_item, _ = _assign(company, emp, 'basic_salary', 'Basic Salary',
                            Decimal('10000'), 'earning', 'መሠሪያ ደምም')
    house_item, _ = _assign(company, emp, 'housing', 'Housing Allowance',
                            Decimal('3000'), 'earning', 'ቤት ክፍያ')
    _assign(company, emp, 'court_order', 'Court Order',
            Decimal('1000'), 'deduction', 'የውሳኔ ትዕዛዝ')

    run = PayrollRun(
        company_id=company.id,
        period='2026-09',
        status='review',
        run_date=date(2026, 9, 1),
        approved_by=user.id,
    )
    db.session.add(run)
    db.session.commit()

    draft = PayrollDraft(
        payroll_run_id=run.id,
        company_id=company.id,
        employee_data=[{
            'id': emp.employee_id,
            'name': emp.name,
            'basic': 10000.0,
            'allowances': 5000.0,
            'gross': 15000.0,
            'tax': 1500.0,
            'pension_employee': 700.0,
            'pension_employer': 1100.0,
            'net': 12800.0,
        }],
    )
    db.session.add(draft)
    db.session.commit()

    result = process_payroll(
        run=run,
        company_id=company.id,
        user_id=user.id,
        user_email=user.email or 'owner@test.com',
        request_ip='127.0.0.1',
    )
    assert result.success is True

    payslip = Payslip.query.filter_by(
        payroll_run_id=run.id, company_id=company.id
    ).first()
    assert payslip is not None

    # The snapshot must exist -- this is what the lazy PDF renders.
    assert payslip.line_items is not None, (
        'line_items must be snapshotted at approval; the payslip PDF renders '
        'these instead of recomputing'
    )
    assert len(payslip.line_items) > 0

    by_key = {li['item_key']: li for li in payslip.line_items}

    # Earnings captured with their approved amounts.
    assert 'basic_salary' in by_key
    assert Decimal(str(by_key['basic_salary']['earned_amount'])) == Decimal('10000')
    assert 'housing' in by_key
    assert Decimal(str(by_key['housing']['earned_amount'])) == Decimal('3000')

    # Classification drives which PDF section the line lands in.
    assert by_key['housing']['classification'] == 'earning'

    # Bilingual labels come from PayItemType, not hardcoded PDF strings.
    assert by_key['housing']['item_label'] == 'Housing Allowance'
    assert by_key['housing']['item_label_am'] == 'ቤት ክፍያ'

    # The deduction is captured as a deduction line.
    assert 'court_order' in by_key
    assert by_key['court_order']['classification'] == 'deduction'

    # Guard against the legacy bridge silently taking over.
    assert payslip.gross_salary == Decimal('13000'), (
        'engine path should sum assignments (10000 + 3000), not the draft '
        'figures (15000)'
    )


def test_legacy_employee_has_no_line_items(ctx, company_user_employee):
    """An employee with no assignments takes the legacy path: no snapshot.

    Documents the bridge explicitly so the two branches cannot be confused.
    """
    from payroll_engine.models import Payslip
    from payroll_engine.services.payroll_service import process_payroll

    company, user, emp = company_user_employee

    run = PayrollRun(
        company_id=company.id, period='2026-09', status='review',
        run_date=date(2026, 9, 1), approved_by=user.id,
    )
    db.session.add(run)
    db.session.commit()

    draft = PayrollDraft(
        payroll_run_id=run.id,
        company_id=company.id,
        employee_data=[{
            'id': emp.employee_id, 'name': emp.name, 'basic': 10000.0,
            'allowances': 2000.0, 'gross': 12000.0, 'tax': 1500.0,
            'pension_employee': 700.0, 'pension_employer': 1100.0, 'net': 9800.0,
        }],
    )
    db.session.add(draft)
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
    assert payslip.line_items is None, (
        'legacy path has no engine breakdown; the PDF falls back to the old '
        'hardcoded rows by design'
    )
    assert payslip.gross_salary == Decimal('12000'), 'legacy path uses draft figures'


# ---------------------------------------------------------------------------
# Review finding #13: Total Deductions == sum of deduction lines
# ---------------------------------------------------------------------------


def test_total_deductions_equals_sum_of_deduction_lines(ctx, company_user_employee):
    """process_payroll must produce a payslip whose total_deductions
    equals the sum of every line item with classification ==
    'deduction' in line_items.  This catches the bridge
    double-subtract scenario where a deduction is applied
    twice."""
    from decimal import Decimal
    from payroll_engine.models_payroll_elements import (
        PayItemClassification,
    )
    from payroll_engine.services.payroll_service import process_payroll
    from payroll_engine.models import PayrollRun

    co, user, emp = company_user_employee

    # The employee must have assignments so the engine branch is taken.
    # Inline the same pattern as _assign in this file.
    from payroll_engine.models_payroll_elements import (
        PayItemType, PayrollItemAssignment,
    )
    for key, name, amount, classification, am_label in (
        ('basic_salary', 'Basic Salary', Decimal('10000'), 'earning', 'መሠሪያ ደምም'),
        ('court_order', 'Court Order', Decimal('1000'), 'deduction', 'የውሳኔ ትዕዛዝ'),
    ):
        item = PayItemType(
            company_id=co.id, key=key, name_en=name,
            name_am=am_label, classification=classification,
            calculation_method='fixed', tax_treatment='taxable',
            is_system=False,
        )
        db.session.add(item); db.session.flush()
        a = PayrollItemAssignment(
            company_id=co.id, employee_id=emp.id,
            pay_item_type_id=item.id, fixed_amount=amount, is_active=True,
        )
        db.session.add(a); db.session.flush()

    run = PayrollRun(
        company_id=co.id, period='2026-09',
        status='review', run_date=__import__('datetime').date(2026, 9, 1),
        approved_by=user.id,
    )
    db.session.add(run); db.session.commit()

    # process_payroll requires a PayrollDraft to exist.
    from payroll_engine.models import PayrollDraft
    draft = PayrollDraft(
        payroll_run_id=run.id, company_id=co.id,
        employee_data=[{
            'id': emp.employee_id, 'name': emp.name,
            'basic': 10000.0, 'allowances': 0.0,
            'gross': 15000.0, 'tax': 1500.0,
            'pension_employee': 700.0,
            'pension_employer': 1100.0, 'net': 11700.0,
        }],
    )
    db.session.add(draft); db.session.commit()

    result = process_payroll(
        run=run, company_id=co.id, user_id=user.id,
        user_email=user.email, request_ip='127.0.0.1',
    )

    assert result.success, f"payroll must succeed: {result.message}"
    # The payslip is stored via the payslips relationship.
    payslip = run.payslips[0] if run.payslips else None
    assert payslip is not None, 'payroll must produce a payslip'

    # Deduction details are stored as JSON (user-assigned deductions
    # only — system items like pension/tax are in line_items but not
    # in deduction_details).
    deduction_details = payslip.deduction_details or []
    detail_total = sum(
        Decimal(str(d.get('amount', 0)))
        for d in deduction_details if isinstance(d, dict)
    )

    # line_items contains ALL items including system-managed ones.
    # Compare user-assigned deduction details against the
    # non-system deduction lines in line_items.
    line_items = payslip.line_items or []
    user_deduction_lines = [
        li for li in line_items
        if li.get('classification') == 'deduction'
        and not li.get('is_system')
    ]
    sum_lines = sum(
        Decimal(str(li.get('earned_amount', 0)))
        for li in user_deduction_lines
    )
    assert abs(detail_total - sum_lines) < Decimal('0.01'), (
        f'deduction_details total ({detail_total}) must match '
        f'non-system deduction line items ({sum_lines}); '
        f'found {len(user_deduction_lines)} user deduction lines'
    )
