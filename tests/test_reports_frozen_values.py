"""Reports for an approved/locked month must use the month's FROZEN figures.

Audit finding (PLAN.md Next item 2): the PAYE (ERCA) and pension schedules read
``employee.basic_salary`` -- today's salary -- so re-downloading a locked month
after a raise gave different numbers. This file approves a month, locks it,
changes the employees' salaries, then regenerates every monthly output and
asserts the figures equal the originally approved values.

Two employees:
- ENGINE: has pay-item assignments (basic + housing) and overtime, so the
  payslip carries a line_items snapshot with the approved basic.
- LEGACY: no assignments, so process_payroll takes the legacy bridge. Basic
  salary and taxable income are NOT stored on such a payslip; reports must
  leave the basic blank and say so, never show today's salary.
"""

import csv
import io
from datetime import date
from decimal import Decimal

import openpyxl
import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, PayrollDraft, PayrollRun, Payslip, User

PERIOD_YEAR = 2026


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
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _assign(company, emp, key, name, amount, tax_treatment='taxable'):
    from payroll_engine.models_payroll_elements import PayItemType, PayrollItemAssignment

    item = PayItemType.query.filter_by(company_id=company.id, key=key).first()
    if item is None:
        item = PayItemType(
            company_id=company.id,
            key=key,
            name_en=name,
            classification='earning',
            calculation_method='fixed',
            tax_treatment=tax_treatment,
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
    return a


@pytest.fixture
def locked_month(app):
    """Approve and lock one month for an engine employee and a legacy employee."""
    from payroll_engine.services.payroll_service import process_payroll

    company = Company(name='FrozenCo', tin='0000000001')
    db.session.add(company)
    db.session.commit()
    owner = User(phone='0911000777', company_id=company.id, role='owner', email='owner@frozen.test')
    owner.set_password('Test1234!')
    db.session.add(owner)
    engine_emp = Employee(
        employee_id='EMP001',
        name='Abebe Engine',
        basic_salary=Decimal('10000'),
        allowances=Decimal('3000'),
        bank_or_telebirr='1000123456789',
        company_id=company.id,
    )
    legacy_emp = Employee(
        employee_id='EMP002',
        name='Sara Legacy',
        basic_salary=Decimal('6000'),
        allowances=Decimal('0'),
        bank_or_telebirr='1000987654321',
        company_id=company.id,
    )
    db.session.add_all([engine_emp, legacy_emp])
    db.session.commit()

    basic_a = _assign(company, engine_emp, 'basic_salary', 'Basic Salary', Decimal('10000'))
    housing_a = _assign(company, engine_emp, 'housing', 'Housing Allowance', Decimal('3000'))

    run = PayrollRun(
        company_id=company.id,
        period=f'{PERIOD_YEAR}-09',
        status='review',
        run_date=date(PERIOD_YEAR, 9, 1),
        approved_by=owner.id,
    )
    db.session.add(run)
    db.session.commit()
    db.session.add(
        PayrollDraft(
            payroll_run_id=run.id,
            company_id=company.id,
            employee_data=[
                {
                    'id': 'EMP001',
                    'name': 'Abebe Engine',
                    'basic': 10000.0,
                    'allowances': 3000.0,
                    'gross': 13000.0,
                    'tax': 0.0,
                    'pension_employee': 0.0,
                    'pension_employer': 0.0,
                    'net': 13000.0,
                    'bank': '1000123456789',
                    'overtime': [{'hours': 4, 'type': 'day'}],
                },
                {
                    # Legacy bridge: these pre-computed figures are what is paid.
                    'id': 'EMP002',
                    'name': 'Sara Legacy',
                    'basic': 6000.0,
                    'allowances': 0.0,
                    'gross': 6000.0,
                    'tax': 665.0,
                    'pension_employee': 420.0,
                    'pension_employer': 660.0,
                    'net': 4915.0,
                    'bank': '1000987654321',
                },
            ],
        )
    )
    db.session.commit()

    result = process_payroll(
        run=run, company_id=company.id, user_id=owner.id, user_email=owner.email, request_ip='127.0.0.1'
    )
    assert result.success is True
    run = db.session.get(PayrollRun, run.id)
    assert run.status == 'completed'
    run.status = 'locked'
    db.session.commit()

    return {
        'company_id': company.id,
        'owner_id': owner.id,
        'run_id': run.id,
        'engine_emp_id': engine_emp.id,
        'legacy_emp_id': legacy_emp.id,
        'basic_assignment_id': basic_a.id,
        'housing_assignment_id': housing_a.id,
    }


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True


def _xlsx_rows(data):
    """Workbook cell values, dropping the 'Generated: <today>' line."""
    wb = openpyxl.load_workbook(io.BytesIO(data))
    rows = []
    for row in wb.active.iter_rows(values_only=True):
        if row and isinstance(row[0], str) and row[0].startswith('Generated:'):
            continue
        rows.append(row)
    return rows


def _row_for(rows, name):
    return next(r for r in rows if r and name in r)


def _payslips(ctx):
    return (
        Payslip.query.filter_by(payroll_run_id=ctx['run_id'], company_id=ctx['company_id'])
        .order_by(Payslip.employee_id)
        .all()
    )


def _generate_everything(client, ctx):
    """Regenerate every monthly output for the locked run."""
    from payroll_engine import pdf as pdf_mod
    from payroll_engine.reports import (
        _generate_erca_csv,
        _generate_pension_csv,
        generate_erca_report,
        generate_pension_report,
        generate_yearly_summary,
    )

    company = db.session.get(Company, ctx['company_id'])
    payslips = _payslips(ctx)
    out = {
        'erca_default': _xlsx_rows(generate_erca_report(payslips, company.name, 'September 2026')),
        'erca_template': _xlsx_rows(generate_erca_report(payslips, company.name, 'September 2026', company=company)),
        'pension': _xlsx_rows(generate_pension_report(payslips, company.name, 'September 2026')),
        'erca_csv': list(csv.reader(io.StringIO(_generate_erca_csv(payslips, company.name, 'Sep').decode()))),
        'pension_csv': list(csv.reader(io.StringIO(_generate_pension_csv(payslips, company.name, 'Sep').decode()))),
        'yearly': _xlsx_rows(generate_yearly_summary(payslips, company.name, PERIOD_YEAR)),
    }

    # HTTP routes, as the accountant downloads them (locked run).
    _login(client, ctx['owner_id'])
    for key, url in (
        ('route_erca', f'/reports/erca/{ctx["run_id"]}'),
        ('route_pension', f'/reports/pension/{ctx["run_id"]}'),
        ('route_bank', f'/reports/bank/{ctx["run_id"]}?format=xlsx'),
        ('route_yearly', f'/reports/yearly/{PERIOD_YEAR}'),
    ):
        resp = client.get(url)
        assert resp.status_code == 200, f'{url} -> {resp.status_code}'
        assert resp.mimetype.endswith('spreadsheetml.sheet'), f'{url} did not return a workbook'
        out[key] = _xlsx_rows(resp.data)
    resp = client.get('/payroll/payslips/export')
    assert resp.status_code == 200
    out['payslip_export'] = list(csv.reader(io.StringIO(resp.data.decode())))

    # Payslip PDF regeneration: capture the data the PDF would render.
    captured = {}

    def _fake_generate(emp_data, company=None, output_dir=None, file_key=None):
        captured[emp_data['id']] = {
            k: emp_data.get(k) for k in ('basic', 'allowances', 'gross', 'tax', 'net', 'taxable')
        }
        return '/tmp/fake.pdf'

    original = pdf_mod.generate_payslip
    pdf_mod.generate_payslip = _fake_generate
    try:
        for p in _payslips(ctx):
            p.pdf_status = 'not_generated'
            p.pdf_file_path = None
            db.session.flush()
            pdf_mod._ensure_pdf(p, p.employee)
    finally:
        pdf_mod.generate_payslip = original
        db.session.rollback()
    out['pdf'] = captured
    return out


def _raise_salaries(ctx):
    from payroll_engine.models_payroll_elements import PayrollItemAssignment

    engine_emp = db.session.get(Employee, ctx['engine_emp_id'])
    legacy_emp = db.session.get(Employee, ctx['legacy_emp_id'])
    engine_emp.basic_salary = Decimal('15000')
    engine_emp.allowances = Decimal('5000')
    legacy_emp.basic_salary = Decimal('9000')
    db.session.get(PayrollItemAssignment, ctx['basic_assignment_id']).fixed_amount = Decimal('15000')
    db.session.get(PayrollItemAssignment, ctx['housing_assignment_id']).fixed_amount = Decimal('5000')
    db.session.commit()


def test_locked_month_reports_unchanged_after_salary_change(client, locked_month):
    ctx = locked_month
    engine_ps, legacy_ps = _payslips(ctx)
    approved = {
        'gross': engine_ps.gross_salary,
        'taxable': engine_ps.taxable_income,
        'tax': engine_ps.tax,
        'pen_emp': engine_ps.employee_pension,
        'pen_empr': engine_ps.employer_pension,
        'net': engine_ps.net_pay,
    }
    # Sanity: the engine payslip froze basic 10,000 + housing 3,000 + overtime.
    assert approved['gross'] > Decimal('13000')
    assert approved['pen_emp'] == Decimal('700.00')
    assert approved['pen_empr'] == Decimal('1100.00')
    assert approved['taxable'] is not None
    assert legacy_ps.line_items is None and legacy_ps.taxable_income is None

    before = _generate_everything(client, ctx)
    _raise_salaries(ctx)
    after = _generate_everything(client, ctx)

    # 1) Every output is identical before and after the raise.
    for key in before:
        assert after[key] == before[key], f'{key} changed after a salary change on a locked month'

    # 2) ...and the figures are the approved values, not today's salary.
    pension_row = _row_for(after['pension'], 'Abebe Engine')
    assert pension_row[3] == 10000  # basic frozen at approval, not 15,000
    assert Decimal(str(pension_row[4])) == approved['pen_emp']
    assert Decimal(str(pension_row[5])) == approved['pen_empr']
    assert Decimal(str(pension_row[6])) == approved['pen_emp'] + approved['pen_empr']

    for key in ('erca_default', 'erca_template', 'route_erca'):
        rows = after[key]
        header = next(r for r in rows if r and 'Basic Salary' in r)
        row = _row_for(rows, 'Abebe Engine')
        cell = dict(zip(header, row, strict=False))
        assert cell['Basic Salary'] == 10000, key
        assert Decimal(str(cell['Total Taxable'])) == approved['taxable'], key
        assert Decimal(str(cell['Tax withheld'])) == approved['tax'], key
        overtime = Decimal(str(cell['Over Time']))
        assert overtime > 0, key
        # transport/other column = gross - frozen basic - overtime (3,000 housing)
        assert Decimal(str(cell['Transport Allowance'])) == Decimal('3000'), key

    erca_csv_row = _row_for(after['erca_csv'], 'Abebe Engine')
    assert Decimal(erca_csv_row[3]) == Decimal('10000')
    assert Decimal(erca_csv_row[8]) == approved['taxable']
    assert Decimal(erca_csv_row[9]) == approved['tax']
    pension_csv_row = _row_for(after['pension_csv'], 'Abebe Engine')
    assert Decimal(pension_csv_row[3]) == Decimal('10000')

    yearly_row = _row_for(after['yearly'], 'Abebe Engine')
    assert Decimal(str(yearly_row[3])) == approved['gross']
    assert Decimal(str(yearly_row[5])) == approved['tax']
    assert Decimal(str(yearly_row[6])) == approved['net']

    flat_bank = [c for r in after['route_bank'] for c in (r or ()) if c is not None]
    assert any(Decimal(str(c)) == approved['net'] for c in flat_bank if isinstance(c, (int, float, Decimal))), (
        f'bank file must pay the approved net {approved["net"]}'
    )

    export_header = after['payslip_export'][0]
    export_row = dict(zip(export_header, _row_for(after['payslip_export'], 'EMP001'), strict=False))
    assert Decimal(export_row['Basic Salary']) == Decimal('10000')
    assert Decimal(export_row['Taxable Income']) == approved['taxable']

    assert after['pdf']['EMP001']['basic'] == Decimal('10000.00')
    assert after['pdf']['EMP001']['gross'] == approved['gross']
    assert after['pdf']['EMP001']['taxable'] == approved['taxable']

    # 3) Legacy payslip: basic was never stored. Blank + explicit note, never
    #    today's 9,000 (or the approved 6,000 guessed from elsewhere).
    legacy_pension = _row_for(after['pension'], 'Sara Legacy')
    assert legacy_pension[3] in (None, '')
    assert Decimal(str(legacy_pension[4])) == Decimal('420.00')
    flat_pension = [c for r in after['pension'] for c in (r or ()) if isinstance(c, str)]
    assert any('not stored with this payroll run' in c for c in flat_pension)
    legacy_erca = _row_for(after['erca_default'], 'Sara Legacy')
    assert 9000 not in legacy_erca and Decimal('9000') not in legacy_erca
    assert after['pdf']['EMP002']['basic'] is None
    assert after['pdf']['EMP002']['gross'] == Decimal('6000.00')


def test_frozen_figures_reads_line_items_not_employee():
    """Unit check of the helper on a plain object (no DB)."""
    from payroll_engine.frozen_payslip import frozen_figures

    class PS:
        gross_salary = Decimal('13288.48')
        tax = Decimal('2000.00')
        employee_pension = Decimal('700.00')
        employer_pension = Decimal('1100.00')
        net_pay = Decimal('10588.48')
        taxable_income = Decimal('12588.48')
        exempt_allowances = Decimal('0.00')
        line_items = [
            {'item_key': 'basic_salary', 'classification': 'earning', 'earned_amount': '10000.00'},
            {'item_key': 'housing', 'classification': 'earning', 'earned_amount': 3000.0},
            {'item_key': 'overtime', 'classification': 'earning', 'earned_amount': '288.48'},
            {'item_key': 'employee_pension', 'classification': 'deduction', 'earned_amount': '700.00'},
        ]

        class employee:  # noqa: N801 -- today's record must be ignored
            basic_salary = Decimal('99999')

    fig = frozen_figures(PS())
    assert fig['basic'] == Decimal('10000.00')
    assert fig['basic_frozen'] is True
    assert fig['overtime'] == Decimal('288.48')
    assert fig['other_earnings'] == Decimal('3000.00')
    assert fig['taxable'] == Decimal('12588.48')

    PS.line_items = None
    PS.taxable_income = None
    fig = frozen_figures(PS())
    assert fig['basic'] is None and fig['basic_frozen'] is False
    assert fig['overtime'] is None and fig['other_earnings'] is None and fig['taxable'] is None
    assert fig['net'] == Decimal('10588.48')
