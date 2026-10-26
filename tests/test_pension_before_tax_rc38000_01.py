"""Pinned behaviour for the PAYE timing switch (RC-38000-01).

Since 2026-10-25 (PLAN.md R1) PAYE is calculated on gross taxable income:
the 7% employee pension is still deducted from pay but does not reduce
taxable income (constants.PENSION_DEDUCTED_BEFORE_TAX = False). Pending an
accountant's written sign-off (reference RC-38000-01); it is NOT attributed
to a statute article here. The legacy rule (pension before tax) stays
available by setting the constant to True.

The pinned case must fail if constants.PENSION_DEDUCTED_BEFORE_TAX is
flipped without a deliberate test update. The flip test proves every
monthly PAYE path honours the constant while the intentional exceptions
(daily workers, comparison explanations) stay unchanged.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import pytest

from payroll_engine import constants
from payroll_engine.payroll import calculate_daily_worker_payroll, calculate_payroll
from payroll_engine.tax import DEFAULT_BRACKETS

QL = Decimal('0.01')

# RC-38000-01 inputs: gross 38,000, basic = gross, no allowances/overtime/other deductions.
RC_BASIC = Decimal('38000')


def _tax_from_default_brackets(taxable: Decimal) -> Decimal:
    """Expected tax derived from the live DEFAULT_BRACKETS table (not a copied value)."""
    tax = Decimal('0')
    previous_bound = Decimal('0')
    for upper_bound, rate in DEFAULT_BRACKETS:
        if taxable <= previous_bound:
            break
        band = min(taxable, upper_bound) - previous_bound
        if band > 0:
            tax += band * rate
        previous_bound = upper_bound
    return tax.quantize(QL, rounding=ROUND_HALF_UP)


def test_pension_before_tax_RC38000_01():
    """Pinned rule (RC-38000-01): PAYE on gross; pension NOT deducted before tax."""
    # Flip guard: flipping the constant must require a deliberate test update.
    assert constants.PENSION_DEDUCTED_BEFORE_TAX is False

    result = calculate_payroll(basic_salary=RC_BASIC)

    assert result['pension_employee'] == Decimal('2660.00')
    assert result['taxable'] == Decimal('38000.00')
    assert result['tax'] == Decimal('11250.00')
    assert result['net'] == Decimal('24090.00')

    # Derived from the existing bracket table, not copied values.
    assert result['tax'] == _tax_from_default_brackets(result['taxable'])


def test_pension_before_tax_RC38000_01_excel_engine():
    """Same pinned case through the Excel-compatible engine path."""
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    result = ExcelPayrollEngine(company_id=1, for_date='2026-08-01').calculate_employee(
        employee_id='RC38',
        name='RC-38000-01',
        basic_salary=RC_BASIC,
    )

    assert result.pension_employee == Decimal('2660.00')
    assert result.taxable == Decimal('38000.00')
    assert result.tax == Decimal('11250.00')
    assert result.net == Decimal('24090.00')


def test_flip_changes_every_monthly_paye_path(app_for_elements, system_catalog_for_elements, monkeypatch):
    """Flipping the constant must change PAYE on every monthly path, and never
    change the daily-worker exception or the comparison explanation."""
    from payroll_engine.excel_payroll import ExcelPayrollEngine
    from payroll_engine.impact import preview_allowance_change, preview_termination
    from payroll_engine.models import Employee
    from payroll_engine.payroll import generate_calculation_flow
    from payroll_engine.services.settlement_service import calculate_settlement

    tax_on_full_gross = _tax_from_default_brackets(RC_BASIC)  # 11,250.00 for 38,000

    # --- Baseline with the legacy rule switched on (True) ---
    monkeypatch.setattr(constants, 'PENSION_DEDUCTED_BEFORE_TAX', True)
    daily_true = calculate_daily_worker_payroll(Decimal('200'), 2)

    legacy_true = calculate_payroll(basic_salary=RC_BASIC)
    assert legacy_true['taxable'] == Decimal('35340.00')

    excel_true = ExcelPayrollEngine(company_id=1, for_date='2026-08-01').calculate_employee(
        employee_id='RC38', name='RC-38000-01', basic_salary=RC_BASIC
    )
    assert excel_true.taxable == Decimal('35340.00')

    # Catalog/elements engine (used by the worksheet workflow).
    elements_true = _render_elements_result(system_catalog_for_elements)
    assert elements_true['taxable'] == Decimal('35340.00')

    settlement_employee = Employee(basic_salary=RC_BASIC, allowances=Decimal('0'), start_date=date(2025, 1, 1))
    settlement_true = calculate_settlement(settlement_employee, 'resignation', date(2026, 9, 30), 1, db_session=None)
    assert settlement_true['tax_on_salary'] == Decimal('10319.00')

    termination_true = preview_termination(
        basic_salary=RC_BASIC,
        allowances=Decimal('0'),
        start_date=date(2025, 1, 1),
        end_date=date(2026, 9, 30),
        termination_reason='resignation',
    )
    assert termination_true['breakdown']['tax'] == Decimal('10319.00')

    # Impact previews (management what-if screens). The allowance what-if
    # reports only marginal changes, so use a basic salary where the flag
    # moves the result across a bracket boundary (14,500: taxable is
    # 13,485 with the deduction, 14,500 without).
    allowance_basic = Decimal('14500')
    allowance_tax_change_true = preview_allowance_change(
        current_amount=Decimal('0'),
        new_amount=Decimal('1000'),
        basic_salary=allowance_basic,
        allowance_type='other',
    )['impact']['tax_change']
    assert allowance_tax_change_true == (
        _tax_from_default_brackets(Decimal('14485')) - _tax_from_default_brackets(Decimal('13485'))
    )

    # --- Flip to the committed default (False = PAYE on gross) ---
    monkeypatch.setattr(constants, 'PENSION_DEDUCTED_BEFORE_TAX', False)

    # Legacy monthly engine: taxable no longer includes the pension deduction.
    legacy_false = calculate_payroll(basic_salary=RC_BASIC)
    assert legacy_false['taxable'] == RC_BASIC
    assert legacy_false['tax'] == tax_on_full_gross
    # Hard literals (RC-38000-01): flipped taxable 38,000 → tax 11,250.00 and
    # net 24,090.00. Derived from the live bracket table today; hard-coding
    # them here also guards against silent bracket-table drift.
    assert tax_on_full_gross == Decimal('11250.00')
    assert legacy_false['tax'] == Decimal('11250.00')
    assert legacy_false['net'] == Decimal('24090.00')
    assert legacy_false['pension_employee'] == Decimal('2660.00')  # still deducted from pay
    assert legacy_false['tax'] != legacy_true['tax']

    # Excel-compatible engine.
    excel_false = ExcelPayrollEngine(company_id=1, for_date='2026-08-01').calculate_employee(
        employee_id='RC38', name='RC-38000-01', basic_salary=RC_BASIC
    )
    assert excel_false.taxable == RC_BASIC
    assert excel_false.tax == tax_on_full_gross
    assert excel_false.tax != excel_true.tax

    # Catalog/elements engine.
    elements_false = _render_elements_result(system_catalog_for_elements)
    assert elements_false['taxable'] == RC_BASIC
    assert elements_false['tax'] == tax_on_full_gross
    assert elements_false['tax'] != elements_true['tax']

    # Settlement path.
    settlement_false = calculate_settlement(settlement_employee, 'resignation', date(2026, 9, 30), 1, db_session=None)
    assert settlement_false['tax_on_salary'] == tax_on_full_gross
    assert settlement_false['tax_on_salary'] != settlement_true['tax_on_salary']

    # Impact previews (management what-if screens).
    termination_false = preview_termination(
        basic_salary=RC_BASIC,
        allowances=Decimal('0'),
        start_date=date(2025, 1, 1),
        end_date=date(2026, 9, 30),
        termination_reason='resignation',
    )
    assert termination_false['breakdown']['tax'] == tax_on_full_gross
    assert termination_false['breakdown']['tax'] != termination_true['breakdown']['tax']

    allowance_tax_change_false = preview_allowance_change(
        current_amount=Decimal('0'),
        new_amount=Decimal('1000'),
        basic_salary=allowance_basic,
        allowance_type='other',
    )['impact']['tax_change']
    assert allowance_tax_change_false == (
        _tax_from_default_brackets(Decimal('15500')) - _tax_from_default_brackets(Decimal('14500'))
    )
    assert allowance_tax_change_false != allowance_tax_change_true

    # Exceptions must be UNMOVED by the flip.
    daily_false = calculate_daily_worker_payroll(Decimal('200'), 2)
    assert daily_false['tax'] == daily_true['tax']
    assert daily_false['taxable'] == daily_true['taxable']

    # Comparison explanation adapts (savings shown as zero when the deduction
    # is no longer pre-tax); it is not gated by the constant.
    flow = generate_calculation_flow(
        {
            'gross': RC_BASIC,
            'taxable': legacy_false['taxable'],
            'tax': legacy_false['tax'],
            'net': legacy_false['net'],
            'pension_employee': Decimal('2660.00'),
            'exempt_allowances': Decimal('0'),
        }
    )
    assert flow['pension_savings'] == Decimal('0')


def test_notice_switch_defaults_on_and_can_be_disabled(monkeypatch):
    """Single documented switch for the RC-38000-01 notice (default on)."""
    monkeypatch.delenv('PAYROLL_PENDING_TAX_NOTICE', raising=False)
    assert constants.PENDING_CONFIRMATION_NOTICE is True
    assert constants.pending_paye_notice_enabled() is True

    monkeypatch.setenv('PAYROLL_PENDING_TAX_NOTICE', '0')
    assert constants.pending_paye_notice_enabled() is False

    monkeypatch.setenv('PAYROLL_PENDING_TAX_NOTICE', '1')
    assert constants.pending_paye_notice_enabled() is True

    # Deployment override wins over the constant while it is set.
    monkeypatch.setattr(constants, 'PENDING_CONFIRMATION_NOTICE', False)
    assert constants.pending_paye_notice_enabled() is True  # env '1' overrides constant
    monkeypatch.delenv('PAYROLL_PENDING_TAX_NOTICE')
    assert constants.pending_paye_notice_enabled() is False  # constant False with no env
    monkeypatch.setattr(constants, 'PENDING_CONFIRMATION_NOTICE', True)

    text = constants.PENDING_PAYE_NOTICE_TEXT
    assert 'RC-38000-01' in text
    assert '979/2016' in text

    # RC-38000-01 closed: the notice cites the proclamation, not a single article.
    assert 'Proclamation No. 979/2016' in text
    assert 'Article' not in text


# ---------------------------------------------------------------------------
# Fixtures for the catalog/elements path (mirrors tests/test_elements_engine.py).
# ---------------------------------------------------------------------------


@pytest.fixture
def app_for_elements():
    from payroll_engine import create_app, db

    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    flask_app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def system_catalog_for_elements(app_for_elements):
    """Create the system catalog item + company-scoped copy + employee fixture.

    Runs inside the app context opened by app_for_elements.
    """
    from payroll_engine import db
    from payroll_engine.models import (
        Company,
        Employee,
        PayItemCalcMethod,
        PayItemClassification,
        PayItemTaxTreatment,
        PayItemType,
        PayrollItemAssignment,
    )
    from payroll_engine.payroll_elements import seed_pay_item_types

    company = Company(name='RC38 Test PLC')
    db.session.add(company)
    db.session.flush()

    db.session.add(
        PayItemType(
            company_id=None,
            key='basic_salary',
            name_en='Basic Salary',
            name_am='የመሰረታዊ ደመወዝ',
            classification=PayItemClassification.EARNING,
            calculation_method=PayItemCalcMethod.FIXED,
            tax_treatment=PayItemTaxTreatment.TAXABLE,
            sort_order=1,
            is_system=True,
        )
    )
    db.session.flush()
    seed_pay_item_types(company.id)
    db.session.flush()

    basic_type = db.session.query(PayItemType).filter_by(company_id=company.id, key='basic_salary').one()
    employee = Employee(
        company_id=company.id,
        employee_id='RC38',
        name='RC-38000-01',
        phone='0912345678',
        basic_salary=RC_BASIC,
    )
    db.session.add(employee)
    db.session.flush()
    db.session.add(
        PayrollItemAssignment(
            company_id=company.id,
            employee_id=employee.id,
            pay_item_type_id=basic_type.id,
            fixed_amount=RC_BASIC,
        )
    )
    db.session.flush()
    return company


def _render_elements_result(company):
    """Calculate through the elements engine inside the open app context."""
    from payroll_engine import db
    from payroll_engine.models import Employee
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    company_id = company.id
    employee = db.session.query(Employee).filter_by(company_id=company_id, employee_id='RC38').one()
    return calculate_payroll_from_assignments(employee, company_id, date(2025, 9, 25))
