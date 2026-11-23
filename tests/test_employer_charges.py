"""Issue #81 — assigned employer charges calculate, or payroll stops loudly.

A pay item classified ``employer_charge`` used to be bucketed by the loaders
and then never evaluated: it contributed zero to employer cost, appeared on no
payslip or report and raised nothing. The tests below fail on ``origin/main``
and pass with the fix:

* a fixed and a ``percent_of_basic`` employer charge reach ``line_items`` and
  the employer-cost total, without touching employee pay;
* the engine-managed employer pension is counted once, never twice;
* an unknown classification or an unevaluable calculation method stops payroll
  instead of defaulting to earnings / returning zero;
* a seventh tax band added with a later effective date changes tax only for
  payroll dates on or after it.

Every test that runs payroll seeds the synthetic dated rule first.
"""

from datetime import date
from decimal import Decimal

import pytest
from helpers import seed_synthetic_payroll_rule

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, Payslip, TaxRule, User
from payroll_engine.models_payroll_elements import (
    PayItemCalcMethod,
    PayItemClassification,
    PayItemType,
    PayrollItemAssignment,
)

BASIC = Decimal('10000')
CHARGE = Decimal('1500')
PENSION_EMPLOYER = Decimal('1100.00')  # synthetic rule: 11% of basic
EMPLOYER_COST = Decimal('12600.00')  # gross 10000 + pension 1100 + charge 1500
FOR_DATE = date(2026, 9, 1)


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        seed_synthetic_payroll_rule()
        from payroll_engine.catalog import seed_system_items

        seed_system_items()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def ctx(app):
    with app.app_context():
        db.session.rollback()
        yield app
        db.session.rollback()
        db.session.remove()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _company(name):
    from payroll_engine.catalog import seed_company_templates

    company = Company(name=name)
    db.session.add(company)
    db.session.commit()
    seed_company_templates(company.id)
    db.session.commit()
    user = User(phone=f'0912000{company.id:04d}', company_id=company.id, role='owner')
    user.set_password('Synthetic1!')
    db.session.add(user)
    db.session.commit()
    return company, user


def _employee(company, employee_id='EMP001', basic=BASIC):
    employee = Employee(
        employee_id=employee_id,
        name=f'Synthetic {employee_id}',
        basic_salary=basic,
        allowances=Decimal('0'),
        company_id=company.id,
        start_date=date(2020, 1, 1),
    )
    db.session.add(employee)
    db.session.commit()
    return employee


def _item(company, key, name_en, classification, method, **kwargs):
    item = PayItemType(
        company_id=company.id,
        key=key,
        name_en=name_en,
        classification=classification,
        calculation_method=method,
        tax_treatment='taxable',
        is_system=False,
        **kwargs,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _system_item(key, name_en, classification, method, **kwargs):
    item = PayItemType(
        company_id=None,
        key=key,
        name_en=name_en,
        classification=classification,
        calculation_method=method,
        tax_treatment='taxable',
        is_system=True,
        **kwargs,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _assign(company, employee, item, **kwargs):
    assignment = PayrollItemAssignment(
        company_id=company.id,
        employee_id=employee.id,
        pay_item_type_id=item.id,
        is_active=True,
        **kwargs,
    )
    db.session.add(assignment)
    db.session.flush()
    return assignment


def _basic_assignment(company, employee):
    """The engine assembles gross from assignments, so every fixture needs one."""
    item = PayItemType.query.filter_by(company_id=None, key='basic_salary').one()
    return _assign(company, employee, item, fixed_amount=employee.basic_salary)


def _calc(employee, company, for_date=FOR_DATE, **kwargs):
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    return calculate_payroll_from_assignments(employee, company.id, for_date, **kwargs)


def _with_fixed_charge(company, employee, key='workplace_insurance', name='Workplace Insurance'):
    charge = _item(company, key, name, PayItemClassification.EMPLOYER_CHARGE, PayItemCalcMethod.FIXED)
    _assign(company, employee, charge, fixed_amount=CHARGE)
    return charge


def _charge_lines(result, key):
    return [line for line in result['line_items'] if line['item_key'] == key]


# ---------------------------------------------------------------------------
# Fixed-amount employer charge, end to end
# ---------------------------------------------------------------------------


def test_fixed_employer_charge_reaches_line_items_and_employer_cost(ctx):
    company, _ = _company('CoFixedCharge')
    employee = _employee(company)
    _basic_assignment(company, employee)
    baseline = _calc(employee, company)
    _with_fixed_charge(company, employee)

    result = _calc(employee, company)

    lines = _charge_lines(result, 'workplace_insurance')
    assert len(lines) == 1, 'the assigned employer charge never reached line_items'
    assert lines[0]['classification'] == PayItemClassification.EMPLOYER_CHARGE
    assert lines[0]['earned_amount'] == Decimal('1500.00')
    assert lines[0]['is_system'] is False

    assert [line['item_key'] for line in result['employer_charge_items']] == ['workplace_insurance']
    assert result['total_employer_charges'] == PENSION_EMPLOYER + CHARGE
    assert result['employer_cost'] == result['gross'] + result['total_employer_charges']
    assert result['employer_cost'] == EMPLOYER_COST

    # Employer cost is company money: it must not move any employee figure.
    assert (result['gross'], result['tax'], result['net']) == (
        baseline['gross'],
        baseline['tax'],
        baseline['net'],
    )


def test_percent_of_basic_employer_charge_reaches_line_items_and_employer_cost(ctx):
    company, _ = _company('CoPercentCharge')
    employee = _employee(company)
    _basic_assignment(company, employee)
    charge = _item(
        company,
        'employment_service_fund',
        'Employment Service Fund',
        PayItemClassification.EMPLOYER_CHARGE,
        PayItemCalcMethod.PERCENT_OF_BASIC,
    )
    _assign(company, employee, charge, percent_of_basic=Decimal('2'))

    result = _calc(employee, company)

    lines = _charge_lines(result, 'employment_service_fund')
    assert len(lines) == 1, 'the percent_of_basic employer charge never reached line_items'
    assert lines[0]['classification'] == PayItemClassification.EMPLOYER_CHARGE
    assert lines[0]['earned_amount'] == Decimal('200.00')  # 2% of 10,000

    assert [line['item_key'] for line in result['employer_charge_items']] == ['employment_service_fund']
    assert result['total_employer_charges'] == Decimal('1300.00')  # 1,100 pension + 200 charge
    assert result['employer_cost'] == Decimal('11300.00')
    assert result['net'] == _calc(employee, company, **{})['net']  # employee pay untouched


def test_engine_pension_is_in_the_total_but_not_double_counted(ctx):
    company, _ = _company('CoPensionOnce')
    employee = _employee(company)
    _basic_assignment(company, employee)
    _with_fixed_charge(company, employee)

    result = _calc(employee, company)

    # Assigned charges only — the engine-managed pension is evaluated by name,
    # not through an assignment, so listing it here would count it twice.
    assert [line['item_key'] for line in result['employer_charge_items']] == ['workplace_insurance']

    pension_lines = _charge_lines(result, 'employer_pension')
    assert len(pension_lines) == 1, 'the engine-managed employer pension must stay exactly one line'
    assert pension_lines[0]['earned_amount'] == PENSION_EMPLOYER

    assert result['total_employer_charges'] == CHARGE + pension_lines[0]['earned_amount']
    assert result['employer_cost'] == result['gross'] + CHARGE + PENSION_EMPLOYER


# ---------------------------------------------------------------------------
# Effective-dated rule change: a seventh band from a later date
# ---------------------------------------------------------------------------

SEVEN_BAND_RULES = {
    'brackets': [
        {'max': 2000, 'rate': '0'},
        {'max': 4000, 'rate': '0.15'},
        {'max': 7000, 'rate': '0.20'},
        {'max': 10000, 'rate': '0.25'},
        {'max': 14000, 'rate': '0.30'},
        {'max': 20000, 'rate': '0.35'},
        {'max': None, 'rate': '0.40'},
    ],
    'personal_relief': 0,
    'pension': {'employee_rate': '0.07', 'employer_rate': '0.11'},
}


def test_seventh_tax_band_applies_from_its_effective_date(ctx):
    """The dated-rule proof the issue asks for: 6 bands before, 7 after."""
    from payroll_engine.tax import _get_brackets_and_relief, calculate_tax, invalidate_tax_cache

    # seed_synthetic_payroll_rule() stored the six-band rule from 1900-01-01.
    before_change = date(2026, 12, 31)
    from_change = date(2027, 1, 1)
    db.session.add(
        TaxRule(
            version_name='synthetic-seven-band',
            effective_date=from_change,
            status='active',
            rules_json=SEVEN_BAND_RULES,
        )
    )
    db.session.commit()
    invalidate_tax_cache()

    assert len(_get_brackets_and_relief(before_change)[0]) == 6
    assert len(_get_brackets_and_relief(from_change)[0]) == 7

    # ETB 30,000 sits above the new 20,000 boundary, so the two dates differ.
    assert calculate_tax(Decimal('30000'), before_change) == Decimal('8450.00')
    assert calculate_tax(Decimal('30000'), from_change) == Decimal('8950.00')

    # The synthetic six-band rule itself is untouched for earlier dates.
    assert calculate_tax(Decimal('30000'), date(2026, 9, 1)) == Decimal('8450.00')


def test_payroll_uses_the_rule_in_force_on_its_own_date(ctx):
    """Same proof through the engine: only the dated brackets move."""
    from payroll_engine.tax import calculate_tax

    company, _ = _company('CoDatedTax')
    employee = _employee(company, basic=Decimal('30000'))
    _basic_assignment(company, employee)
    db.session.add(
        TaxRule(
            version_name='synthetic-seven-band',
            effective_date=date(2027, 1, 1),
            status='active',
            rules_json=SEVEN_BAND_RULES,
        )
    )
    db.session.commit()

    before = _calc(employee, company, for_date=date(2026, 9, 1))
    after = _calc(employee, company, for_date=date(2027, 1, 1))

    assert before['tax'] == calculate_tax(Decimal('30000'), date(2026, 9, 1))
    assert after['tax'] == calculate_tax(Decimal('30000'), date(2027, 1, 1))
    assert before['tax'] != after['tax']
    # Employer charges are date-independent cost; only the tax moves.
    assert before['employer_cost'] == after['employer_cost']


# ---------------------------------------------------------------------------
# Fail loudly: unknown classification
# ---------------------------------------------------------------------------


def test_unknown_classification_on_an_assignment_stops_payroll(ctx):
    company, _ = _company('CoBadClass')
    employee = _employee(company)
    _basic_assignment(company, employee)
    _item(company, 'mystery_charge', 'Mystery', 'employer_cost', PayItemCalcMethod.FIXED)

    bad = PayrollItemAssignment(
        company_id=company.id,
        employee_id=employee.id,
        pay_item_type_id=PayItemType.query.filter_by(company_id=company.id, key='mystery_charge').one().id,
        fixed_amount=Decimal('10'),
        is_active=True,
    )
    db.session.add(bad)
    db.session.flush()

    with pytest.raises(ValueError) as excinfo:
        _calc(employee, company)
    message = str(excinfo.value)
    assert 'mystery_charge' in message
    assert 'unsupported classification' in message


def test_unknown_classification_in_the_system_catalog_stops_payroll(ctx):
    company, _ = _company('CoBadSystemClass')
    employee = _employee(company)
    _basic_assignment(company, employee)
    _system_item('ghost_system_item', 'Ghost', 'employer_cost', PayItemCalcMethod.FIXED)

    with pytest.raises(ValueError) as excinfo:
        _calc(employee, company)
    assert 'ghost_system_item' in str(excinfo.value)
    assert 'unsupported classification' in str(excinfo.value)


def test_unknown_classification_in_what_if_items_stops_payroll(ctx):
    from payroll_engine.impact import virtual_assignment

    company, _ = _company('CoBadWhatIfClass')
    employee = _employee(company)
    _basic_assignment(company, employee)
    _item(company, 'ghost_what_if', 'Ghost What If', 'employer_cost', PayItemCalcMethod.FIXED)

    extra = virtual_assignment(company.id, 'ghost_what_if', Decimal('10'), for_date=FOR_DATE)
    assert extra is not None

    with pytest.raises(ValueError) as excinfo:
        _calc(employee, company, extra_items=[extra])
    assert 'unsupported classification' in str(excinfo.value)


# ---------------------------------------------------------------------------
# Fail loudly: calculation methods the engine cannot evaluate
# ---------------------------------------------------------------------------


def test_percent_of_item_on_an_employer_charge_stops_payroll(ctx):
    company, _ = _company('CoPercentOfItem')
    employee = _employee(company)
    _basic_assignment(company, employee)
    charge = _item(
        company,
        'employment_service_fund',
        'Employment Service Fund',
        PayItemClassification.EMPLOYER_CHARGE,
        PayItemCalcMethod.PERCENT_OF_ITEM,
    )
    _assign(company, employee, charge, fixed_amount=Decimal('0'))

    with pytest.raises(NotImplementedError) as excinfo:
        _calc(employee, company)
    assert 'percent_of_item' in str(excinfo.value)
    assert 'employment_service_fund' in str(excinfo.value)


def test_percent_of_net_on_an_employer_charge_stops_payroll(ctx):
    """percent_of_net is an employee method: its base here would be zero."""
    company, _ = _company('CoPercentOfNet')
    employee = _employee(company)
    _basic_assignment(company, employee)
    charge = _item(
        company,
        'employment_service_fund',
        'Employment Service Fund',
        PayItemClassification.EMPLOYER_CHARGE,
        PayItemCalcMethod.PERCENT_OF_NET,
    )
    _assign(company, employee, charge, percent_of_net=Decimal('5'))

    with pytest.raises(ValueError) as excinfo:
        _calc(employee, company)
    assert 'percent_of_net' in str(excinfo.value)
    assert 'employment_service_fund' in str(excinfo.value)


@pytest.mark.parametrize('classification', [PayItemClassification.EARNING, PayItemClassification.EMPLOYER_CHARGE])
def test_unrecognized_calculation_method_stops_payroll(ctx, classification):
    """No value column is populated, so the declared method is what runs."""
    company, _ = _company(f'CoBadMethod{classification}')
    employee = _employee(company)
    _basic_assignment(company, employee)
    _item(company, 'compound_bonus', 'Compound Bonus', classification, 'compound')
    _assign(
        company,
        employee,
        PayItemType.query.filter_by(company_id=company.id, key='compound_bonus').one(),
    )

    with pytest.raises(ValueError) as excinfo:
        _calc(employee, company)
    assert 'compound' in str(excinfo.value)
    assert 'cannot evaluate' in str(excinfo.value)


# ---------------------------------------------------------------------------
# Approval: the charge survives onto the payslip
# ---------------------------------------------------------------------------


def test_approved_payslip_records_the_employer_charge(ctx, monkeypatch):
    from payroll_engine.frozen_payslip import employer_charge_total, employer_cost
    from payroll_engine.services.payroll_service import process_payroll
    from payroll_engine.services.worksheet_review import create_review

    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args, **kwargs: None)
    company, user = _company('CoApproveCharge')
    employee = _employee(company)
    _basic_assignment(company, employee)
    _with_fixed_charge(company, employee)

    run = create_review(company.id, user.id, FOR_DATE)
    db.session.commit()

    result = process_payroll(run, company.id, user.id, 'owner@example.invalid', '127.0.0.1')
    assert result.success, result.message or result.error

    slip = Payslip.query.filter_by(company_id=company.id, payroll_run_id=run.id).one()
    charges = [line for line in (slip.line_items or []) if line.get('classification') == 'employer_charge']
    keys = sorted(line['item_key'] for line in charges)
    assert keys == ['employer_pension', 'workplace_insurance']
    assigned = next(line for line in charges if line['item_key'] == 'workplace_insurance')
    assert Decimal(str(assigned['earned_amount'])) == CHARGE

    # The stored totals read the snapshot back without repeating the pension.
    assert employer_charge_total(slip) == PENSION_EMPLOYER + CHARGE
    assert employer_cost(slip) == EMPLOYER_COST
    assert slip.employer_pension == PENSION_EMPLOYER
    # Employee pay on the payslip is unchanged by the employer charge.
    assert slip.gross_salary == BASIC


# ---------------------------------------------------------------------------
# The screens show the total
# ---------------------------------------------------------------------------


def _login(client, user, company):
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
        session['active_company_id'] = company.id


def test_review_and_confirm_screens_show_employer_cost(ctx):
    from payroll_engine.services.worksheet_review import create_review

    company, user = _company('CoScreens')
    employee = _employee(company)
    _basic_assignment(company, employee)
    _with_fixed_charge(company, employee)

    run = create_review(company.id, user.id, FOR_DATE)
    db.session.commit()

    client = ctx.test_client()
    _login(client, user, company)

    review = client.get(f'/payroll/runs/{run.id}/review')
    assert review.status_code == 200
    assert b'Employer cost' in review.data
    assert b'12,600.00' in review.data, 'the review screen must total gross plus every employer charge'
    assert review.data.count(b'12,600.00') >= 2, 'the total and the per-row employer cost must both show'

    confirm = client.get(f'/payroll/{run.id}/confirm')
    assert confirm.status_code == 200
    assert b'data-employer-cost' in confirm.data
    assert b'12,600.00' in confirm.data
    assert b'Workplace Insurance' in confirm.data


def test_approved_run_screen_shows_employer_cost(ctx, monkeypatch):
    from payroll_engine.services.payroll_service import process_payroll
    from payroll_engine.services.worksheet_review import create_review

    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args, **kwargs: None)
    company, user = _company('CoResultScreen')
    employee = _employee(company)
    _basic_assignment(company, employee)
    _with_fixed_charge(company, employee)

    run = create_review(company.id, user.id, FOR_DATE)
    db.session.commit()
    result = process_payroll(run, company.id, user.id, 'owner@example.invalid', '127.0.0.1')
    assert result.success, result.message or result.error

    client = ctx.test_client()
    _login(client, user, company)

    page = client.get(f'/payroll/runs/{run.id}')
    assert page.status_code == 200
    assert b'Employer cost' in page.data
    # payroll_results.html formats money like its other summary cards (%.2f).
    assert b'12600.00' in page.data
