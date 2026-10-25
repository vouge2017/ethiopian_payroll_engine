"""PAYE on gross taxable income, not after the 7 % employee pension (PLAN.md R1).

Since 2026-10-25 ``constants.PENSION_DEDUCTED_BEFORE_TAX`` is False: the 7 %
employee pension is still deducted from pay, but it no longer reduces taxable
income. Pending an Ethiopian accountant's written confirmation (RC-38000-01).

Worked examples use the Proc. 1395/2025 brackets as implemented in
``payroll_engine/tax.py`` (DEFAULT_BRACKETS):

    0 – 2,000      0 %
    2,000 – 4,000  15 %
    4,000 – 7,000  20 %
    7,000 – 10,000 25 %
    10,000 – 14,000 30 %
    above 14,000   35 %

Hand calculations (basic salary only, no allowances, no overtime):

    basic  3,000: tax = 1,000 × 15 %                                   =   150.00
                  pension 210.00, net 3,000 − 150 − 210                = 2,640.00
    basic  5,000: tax = 2,000 × 15 % + 1,000 × 20 % = 300 + 200          =   500.00
                  pension 350.00, net 5,000 − 500 − 350                = 4,150.00
    basic 10,000: tax = 300 + 3,000 × 20 % + 3,000 × 25 % = 300+600+750  = 1,650.00
                  pension 700.00, net 10,000 − 1,650 − 700             = 7,650.00
    basic 20,000: tax = 300 + 600 + 750 + 4,000 × 30 % + 6,000 × 35 %
                      = 300 + 600 + 750 + 1,200 + 2,100                 = 4,950.00
                  pension 1,400.00, net 20,000 − 4,950 − 1,400          = 13,650.00

The second half of this file proves that already approved / locked payroll
months keep their STORED tax, taxable income and net: the flag change must
never recompute them on export, report, portal or payslip-explanation paths.
"""

from datetime import date
from decimal import Decimal

import pytest

from payroll_engine import constants
from payroll_engine.payroll import calculate_payroll

# (basic, pension, tax, net) — hand-verified above.
WORKED_EXAMPLES = [
    (Decimal('10000'), Decimal('700.00'), Decimal('1650.00'), Decimal('7650.00')),
    (Decimal('3000'), Decimal('210.00'), Decimal('150.00'), Decimal('2640.00')),
    (Decimal('5000'), Decimal('350.00'), Decimal('500.00'), Decimal('4150.00')),
    (Decimal('20000'), Decimal('1400.00'), Decimal('4950.00'), Decimal('13650.00')),
]


def test_flag_defaults_to_gross_income():
    """The committed default is PAYE on gross taxable income (RC-38000-01)."""
    assert constants.PENSION_DEDUCTED_BEFORE_TAX is False


@pytest.mark.parametrize(('basic', 'pension', 'tax', 'net'), WORKED_EXAMPLES)
def test_legacy_engine_worked_examples(basic, pension, tax, net):
    result = calculate_payroll(basic_salary=basic)
    assert result['gross'] == basic
    assert result['taxable'] == basic  # pension does not reduce taxable income
    assert result['pension_employee'] == pension
    assert result['tax'] == tax
    assert result['net'] == net
    assert isinstance(result['tax'], Decimal)


@pytest.mark.parametrize(('basic', 'pension', 'tax', 'net'), WORKED_EXAMPLES)
def test_excel_engine_worked_examples(basic, pension, tax, net):
    from payroll_engine.excel_payroll import ExcelPayrollEngine

    result = ExcelPayrollEngine(company_id=1, for_date='2026-10-01').calculate_employee(
        employee_id='W1', name='Worked example', basic_salary=basic
    )
    assert result.taxable == basic
    assert result.pension_employee == pension
    assert result.tax == tax
    assert result.net == net
    assert result.pension_tax_savings == Decimal('0')


def test_basic_10000_settlement_taxes_gross_outstanding_salary():
    from payroll_engine.models import Employee
    from payroll_engine.services.settlement_service import calculate_settlement

    employee = Employee(basic_salary=Decimal('10000'), allowances=Decimal('0'), start_date=date(2025, 1, 1))
    result = calculate_settlement(employee, 'resignation', date(2026, 9, 30), 1, db_session=None)
    assert result['tax_on_salary'] == Decimal('1650.00')


def test_basic_10000_termination_preview_taxes_gross():
    from payroll_engine.impact import preview_termination

    result = preview_termination(
        basic_salary=Decimal('10000'),
        allowances=Decimal('0'),
        start_date=date(2025, 1, 1),
        end_date=date(2026, 9, 30),
        termination_reason='resignation',
    )
    assert result['breakdown']['tax'] == Decimal('1650.00')


def test_basic_10000_calculation_flow_explains_gross_rule():
    from payroll_engine.payroll import generate_calculation_flow

    flow = generate_calculation_flow(calculate_payroll(basic_salary=Decimal('10000')))
    assert flow['pension_savings'] == Decimal('0')
    assert not [s for s in flow['steps'] if 'Savings' in s['label']]
    taxable_step = next(s for s in flow['steps'] if s['label'] == 'Taxable Income')
    assert taxable_step['amount'] == Decimal('10000.00')
    assert taxable_step['note'] == 'Gross − Exempt Allowances'
    pension_step = next(s for s in flow['steps'] if 'Pension' in s['label'])
    assert 'does not reduce taxable income' in pension_step['note']


def test_freeze_context_records_the_rule_applied():
    from payroll_engine.services.correction_context import freeze_context

    context = freeze_context(date(2026, 10, 25), employee_id='SYN', name='Synthetic', bank='1000000000001')
    assert context['pension_deducted_before_tax'] is False


def test_flag_stays_configurable(monkeypatch):
    """The legacy rule can still be switched back on without a code change."""
    monkeypatch.setattr(constants, 'PENSION_DEDUCTED_BEFORE_TAX', True)
    result = calculate_payroll(basic_salary=Decimal('10000'))
    assert result['taxable'] == Decimal('9300.00')
    assert result['tax'] == Decimal('1475.00')
    assert result['net'] == Decimal('7825.00')


# ---------------------------------------------------------------------------
# Elements (worksheet) engine — the other live calculation engine.
# ---------------------------------------------------------------------------


@pytest.fixture
def elements_app():
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


def _elements_employee(basic):
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

    company = Company(name='Gross PAYE PLC')
    db.session.add(company)
    db.session.flush()
    db.session.add(
        PayItemType(
            company_id=None,
            key='basic_salary',
            name_en='Basic Salary',
            name_am='መሠረታዊ ደመወዝ',
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
        company_id=company.id, employee_id='G1', name='Gross Example', phone='0912345670', basic_salary=basic
    )
    db.session.add(employee)
    db.session.flush()
    db.session.add(
        PayrollItemAssignment(
            company_id=company.id, employee_id=employee.id, pay_item_type_id=basic_type.id, fixed_amount=basic
        )
    )
    db.session.flush()
    return company, employee


@pytest.mark.parametrize(('basic', 'pension', 'tax', 'net'), WORKED_EXAMPLES)
def test_elements_engine_worked_examples(elements_app, basic, pension, tax, net):
    from payroll_engine.payroll_elements import calculate_payroll_from_assignments

    company, employee = _elements_employee(basic)
    result = calculate_payroll_from_assignments(employee, company.id, date(2026, 10, 25))
    assert result['gross'] == basic
    assert result['taxable'] == basic
    assert result['pension_employee'] == pension
    assert result['tax'] == tax
    assert result['net'] == net


# ---------------------------------------------------------------------------
# Locked / approved months keep their stored values (RC-38000-01).
# ---------------------------------------------------------------------------

# Figures as they were approved BEFORE the change (pension deducted first):
# basic 10,000 → taxable 9,300 → tax 1,475 → net 7,825.
LOCKED = {
    'gross_salary': Decimal('10000.00'),
    'taxable_income': Decimal('9300.00'),
    'exempt_allowances': Decimal('0.00'),
    'tax': Decimal('1475.00'),
    'employee_pension': Decimal('700.00'),
    'employer_pension': Decimal('1100.00'),
    'net_pay': Decimal('7825.00'),
}


# A month approved AFTER the change (gross rule): taxable 10,000 → tax 1,650.
APPROVED_GROSS_RULE = {
    'gross_salary': Decimal('10000.00'),
    'taxable_income': Decimal('10000.00'),
    'exempt_allowances': Decimal('0.00'),
    'tax': Decimal('1650.00'),
    'employee_pension': Decimal('700.00'),
    'employer_pension': Decimal('1100.00'),
    'net_pay': Decimal('7650.00'),
}


def _locked_month(app, *, with_taxable=True, values=None):
    from payroll_engine import db
    from payroll_engine.models import Company, Employee, PayrollRun, Payslip, User

    company = Company(name='Locked Month PLC')
    db.session.add(company)
    db.session.flush()
    owner = User(phone='0910000101', role='owner', company_id=company.id)
    owner.set_password('OwnerPass1!')
    emp_user = User(phone='0911000102', role='employee', company_id=company.id)
    emp_user.set_password('EmpPass1!')
    db.session.add_all([owner, emp_user])
    db.session.flush()
    employee = Employee(
        employee_id='L001',
        name='Locked Example',
        phone='0911000102',
        basic_salary=Decimal('10000'),
        allowances=Decimal('0'),
        company_id=company.id,
        user_id=emp_user.id,
    )
    db.session.add(employee)
    db.session.flush()
    run = PayrollRun(company_id=company.id, run_date=date(2026, 9, 1), status='locked')
    run.generate_period()
    db.session.add(run)
    db.session.flush()
    run.generate_reference()
    values = dict(values or LOCKED)
    if not with_taxable:
        values['taxable_income'] = None
        values['exempt_allowances'] = None
    payslip = Payslip(payroll_run_id=run.id, company_id=company.id, employee_id=employee.id, **values)
    db.session.add(payslip)
    db.session.commit()
    return company.id, run.id, payslip.id


def _assert_stored_unchanged(payslip_id, *, with_taxable=True):
    from payroll_engine import db
    from payroll_engine.models import Payslip

    db.session.expire_all()
    ps = db.session.get(Payslip, payslip_id)
    assert ps.tax == LOCKED['tax']
    assert ps.net_pay == LOCKED['net_pay']
    assert ps.gross_salary == LOCKED['gross_salary']
    assert ps.employee_pension == LOCKED['employee_pension']
    if with_taxable:
        assert ps.taxable_income == LOCKED['taxable_income']


def test_locked_month_payslip_export_uses_stored_values(elements_app):
    assert constants.PENSION_DEDUCTED_BEFORE_TAX is False
    _cid, _rid, pid = _locked_month(elements_app)
    client = elements_app.test_client()
    client.post('/auth/login', data={'login_id': '0910000101', 'password': 'OwnerPass1!'})
    resp = client.get('/payroll/payslips/export')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    row = next(line for line in body.splitlines() if 'L001' in line)
    assert '9300.00' in row  # stored taxable, not re-derived 10,000
    assert '1475.00' in row
    assert '7825.00' in row
    assert '1650.00' not in row
    _assert_stored_unchanged(pid)


def test_locked_month_portal_payslip_explains_stored_taxable(elements_app):
    _cid, _rid, pid = _locked_month(elements_app)
    client = elements_app.test_client()
    client.post('/auth/login', data={'login_id': '0911000102', 'password': 'EmpPass1!'})
    resp = client.get(f'/my/payslips/{pid}')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Bracket breakdown on stored taxable 9,300: 25 % on the next 2,300.
    assert 'on next 2,300' in body
    assert '1475.00' in body
    _assert_stored_unchanged(pid)


def test_legacy_locked_payslip_without_taxable_column(elements_app):
    """Rows approved before taxable_income existed were taxed after pension."""
    _cid, _rid, pid = _locked_month(elements_app, with_taxable=False)
    client = elements_app.test_client()
    client.post('/auth/login', data={'login_id': '0911000102', 'password': 'EmpPass1!'})
    resp = client.get(f'/my/payslips/{pid}')
    assert resp.status_code == 200
    assert 'on next 2,300' in resp.get_data(as_text=True)
    _assert_stored_unchanged(pid, with_taxable=False)


def test_locked_month_reports_read_stored_tax(elements_app):
    import io

    import openpyxl

    from payroll_engine import db
    from payroll_engine.models import Payslip
    from payroll_engine.reports import generate_erca_report, generate_pension_report

    _cid, _rid, pid = _locked_month(elements_app)
    ps = db.session.get(Payslip, pid)

    def _cells(data):
        wb = openpyxl.load_workbook(io.BytesIO(data))
        return [c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None]

    erca = _cells(generate_erca_report([ps], 'Locked Month PLC', period='Sep 2026'))
    assert any(Decimal(str(v)) == Decimal('1475.00') for v in erca if isinstance(v, (int, float, Decimal)))
    assert not any(Decimal(str(v)) == Decimal('1650.00') for v in erca if isinstance(v, (int, float, Decimal)))

    pension = _cells(generate_pension_report([ps], 'Locked Month PLC', period='Sep 2026'))
    assert any(Decimal(str(v)) == Decimal('700.00') for v in pension if isinstance(v, (int, float, Decimal)))
    _assert_stored_unchanged(pid)


def test_locked_month_calculation_flow_follows_stored_numbers():
    """A locked payslip's PDF/portal explanation follows how it WAS calculated."""
    from payroll_engine.payroll import generate_calculation_flow

    flow = generate_calculation_flow(
        {
            'gross': LOCKED['gross_salary'],
            'taxable': LOCKED['taxable_income'],
            'tax': LOCKED['tax'],
            'net': LOCKED['net_pay'],
            'pension_employee': LOCKED['employee_pension'],
            'exempt_allowances': LOCKED['exempt_allowances'],
        }
    )
    taxable_step = next(s for s in flow['steps'] if s['label'] == 'Taxable Income')
    assert taxable_step['amount'] == Decimal('9300.00')
    assert taxable_step['note'] == 'Gross − Pension − Exempt Allowances'
    assert flow['pension_savings'] == Decimal('175.00')


def _assert_gross_rule_unchanged(payslip_id):
    from payroll_engine import db
    from payroll_engine.models import Payslip

    db.session.expire_all()
    ps = db.session.get(Payslip, payslip_id)
    assert (ps.taxable_income, ps.tax, ps.net_pay) == (Decimal('10000.00'), Decimal('1650.00'), Decimal('7650.00'))


def test_gross_rule_payslip_export_uses_stored_taxable(elements_app):
    """Export must not re-derive taxable as gross − pension."""
    _cid, _rid, pid = _locked_month(elements_app, values=APPROVED_GROSS_RULE)
    owner = elements_app.test_client()
    owner.post('/auth/login', data={'login_id': '0910000101', 'password': 'OwnerPass1!'})
    body = owner.get('/payroll/payslips/export').get_data(as_text=True)
    row = next(line for line in body.splitlines() if 'L001' in line)
    assert '10000.00,1650.00' in row  # Taxable Income, Income Tax columns
    assert '9300.00' not in row
    _assert_gross_rule_unchanged(pid)


def test_gross_rule_payslip_portal_uses_stored_taxable(elements_app):
    _cid, _rid, pid = _locked_month(elements_app, values=APPROVED_GROSS_RULE)
    emp = elements_app.test_client()
    emp.post('/auth/login', data={'login_id': '0911000102', 'password': 'EmpPass1!'})
    resp = emp.get(f'/my/payslips/{pid}')
    assert resp.status_code == 200
    page = resp.get_data(as_text=True)
    assert 'on next 3,000' in page  # 25 % band 7,000–10,000 fully used
    assert 'on next 2,300' not in page


@pytest.mark.parametrize(
    ('values', 'shown_taxable', 'note'),
    [
        (LOCKED, 'Taxable: ETB 9300.00', 'was deducted before tax'),
        (APPROVED_GROSS_RULE, 'Taxable: ETB 10000.00', 'does not reduce taxable income'),
    ],
)
def test_run_results_screen_shows_stored_taxable(elements_app, values, shown_taxable, note):
    _cid, rid, _pid = _locked_month(elements_app, values=values)
    client = elements_app.test_client()
    client.post('/auth/login', data={'login_id': '0910000101', 'password': 'OwnerPass1!'})
    resp = client.get(f'/payroll/runs/{rid}')
    assert resp.status_code == 200
    page = resp.get_data(as_text=True)
    assert shown_taxable in page
    assert note in page
