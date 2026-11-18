from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, Employee, Payslip, TaxRule, User
from payroll_engine.pension import invalidate_pension_cache
from payroll_engine.services.worksheet_review import create_review
from payroll_engine.tax import invalidate_tax_cache

VALID = {
    'brackets': [
        {'max': 2000, 'rate': '0'},
        {'max': 4000, 'rate': '0.15'},
        {'max': 7000, 'rate': '0.20'},
        {'max': 10000, 'rate': '0.25'},
        {'max': 14000, 'rate': '0.30'},
        {'max': None, 'rate': '0.35'},
    ],
    'personal_relief': 0,
    'pension': {'employee_rate': '0.07', 'employer_rate': '0.11'},
}


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///:memory:')
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite:///:memory:', WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        invalidate_tax_cache()
        invalidate_pension_cache()
        yield app
        db.session.remove()
        db.drop_all()
        invalidate_tax_cache()
        invalidate_pension_cache()


def test_missing_rule_blocks_payroll_without_payslips(app):
    company = Company(name='Synthetic rule test')
    db.session.add(company)
    db.session.flush()
    user = User(company_id=company.id, role='owner', phone='0910000100')
    user.set_password('Synthetic1!')
    employee = Employee(
        company_id=company.id, employee_id='TEST', name='Synthetic Worker', basic_salary=10000, allowances=0
    )
    db.session.add_all([user, employee])
    db.session.commit()
    assert TaxRule.get_active_rule(date(2026, 9, 1)) is None
    with pytest.raises(ValueError, match='rule'):
        create_review(company.id, user.id, date(2026, 9, 1))
    assert Payslip.query.filter_by(company_id=company.id).count() == 0


def test_zero_salary_payroll_still_requires_rules(app):
    from payroll_engine.payroll import calculate_payroll
    from payroll_engine.rule_errors import MissingPayrollRuleError

    with pytest.raises(MissingPayrollRuleError, match='rule'):
        calculate_payroll(Decimal('0'), for_date=date(2026, 9, 1))


def test_daily_payroll_does_not_ignore_missing_pension_configuration(app):
    from payroll_engine.payroll import calculate_daily_worker_payroll
    from payroll_engine.rule_errors import MissingPayrollRuleError

    db.session.add(
        TaxRule(
            version_name='synthetic',
            effective_date=date(2020, 1, 1),
            status='active',
            rules_json=dict(VALID, pension={}),
        )
    )
    db.session.commit()
    with pytest.raises(MissingPayrollRuleError, match=r'pension.*incomplete'):
        calculate_daily_worker_payroll(Decimal('100'), 5)


def test_daily_payroll_keeps_no_pension_when_rules_exist(app):
    from payroll_engine.payroll import calculate_daily_worker_payroll

    db.session.add(
        TaxRule(version_name='synthetic', effective_date=date(2020, 1, 1), status='active', rules_json=VALID)
    )
    db.session.commit()
    result = calculate_daily_worker_payroll(Decimal('500'), 20, for_date=date(2026, 9, 1))
    assert (result['gross'], result['tax'], result['pension_employee'], result['pension_employer']) == (
        Decimal('10000.00'),
        Decimal('1650.00'),
        Decimal('0'),
        Decimal('0'),
    )


@pytest.mark.parametrize('kind', ['tax', 'pension'])
@pytest.mark.parametrize('failure', ['missing', 'lookup'])
def test_missing_or_failed_lookup_is_distinct_and_not_cached(app, monkeypatch, kind, failure):
    from payroll_engine.pension import _get_rates, _rates_cache
    from payroll_engine.rule_errors import MissingPayrollRuleError, PayrollRuleLookupError
    from payroll_engine.tax import _brackets_cache, _get_brackets_and_relief

    if failure == 'lookup':

        def broken(*args, **kwargs):
            raise RuntimeError('synthetic database failure')

        monkeypatch.setattr(TaxRule, 'get_active_rule', broken)
    getter, cache = (_get_brackets_and_relief, _brackets_cache) if kind == 'tax' else (_get_rates, _rates_cache)
    expected = PayrollRuleLookupError if failure == 'lookup' else MissingPayrollRuleError
    with pytest.raises(expected, match=kind):
        getter(date(2026, 9, 1))
    assert not cache


@pytest.mark.parametrize('pension', [None, {}, {'employee_rate': '0.07'}, {'employer_rate': '0.11'}])
def test_incomplete_pension_never_defaults(app, pension):
    from payroll_engine.pension import _get_rates, _rates_cache
    from payroll_engine.rule_errors import MissingPayrollRuleError

    data = dict(VALID, pension=pension)
    db.session.add(TaxRule(version_name='synthetic', effective_date=date(2020, 1, 1), status='active', rules_json=data))
    db.session.commit()
    with pytest.raises(MissingPayrollRuleError, match=r'pension.*incomplete'):
        _get_rates(date(2026, 9, 1))
    assert not _rates_cache


def test_valid_dated_rule_preserves_calculation(app):
    from payroll_engine.pension import employee_pension, employer_pension
    from payroll_engine.tax import calculate_tax

    db.session.add(
        TaxRule(version_name='synthetic', effective_date=date(2020, 1, 1), status='active', rules_json=VALID)
    )
    db.session.commit()
    assert calculate_tax(Decimal('10000'), date(2026, 9, 1)) == Decimal('1650.00')
    assert employee_pension(Decimal('10000'), date(2026, 9, 1)) == Decimal('700.00')
    assert employer_pension(Decimal('10000'), date(2026, 9, 1)) == Decimal('1100.00')


def test_removed_rule_cannot_use_previously_loaded_rates(app):
    from payroll_engine.pension import _get_rates
    from payroll_engine.rule_errors import MissingPayrollRuleError
    from payroll_engine.tax import _get_brackets_and_relief

    rule = TaxRule(version_name='synthetic', effective_date=date(2020, 1, 1), status='active', rules_json=VALID)
    db.session.add(rule)
    db.session.commit()
    _get_brackets_and_relief(date(2026, 9, 1))
    _get_rates(date(2026, 9, 1))
    db.session.delete(rule)
    db.session.commit()
    for get_rules in (_get_brackets_and_relief, _get_rates):
        with pytest.raises(MissingPayrollRuleError, match='missing'):
            get_rules(date(2026, 9, 1))


@pytest.mark.parametrize('brackets', [[], None, [{'max': None}], [{'max': None, 'rate': 'not-a-rate'}]])
def test_incomplete_tax_rule_is_not_cached(app, brackets):
    from payroll_engine.rule_errors import MissingPayrollRuleError
    from payroll_engine.tax import _brackets_cache, _get_brackets_and_relief

    db.session.add(
        TaxRule(
            version_name='synthetic',
            effective_date=date(2020, 1, 1),
            status='active',
            rules_json=dict(VALID, brackets=brackets),
        )
    )
    db.session.commit()
    with pytest.raises(MissingPayrollRuleError, match=r'tax.*incomplete'):
        _get_brackets_and_relief(date(2026, 9, 1))
    assert not _brackets_cache


def test_worksheet_displays_missing_rule_without_creating_payslip(app):
    company = Company(name='Synthetic rule test')
    db.session.add(company)
    db.session.flush()
    user = User(company_id=company.id, role='owner', phone='0910000101')
    user.set_password('Synthetic1!')
    db.session.add_all(
        [
            user,
            Employee(
                company_id=company.id, employee_id='TEST', name='Synthetic Worker', basic_salary=10000, allowances=0
            ),
        ]
    )
    db.session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
        session['active_company_id'] = company.id
    response = client.post(
        '/payroll/spreadsheet/review', data={'period_start': date.today().replace(day=1).isoformat()}
    )
    assert response.status_code == 400
    assert b'rule' in response.data.lower()
    assert b'missing' in response.data.lower()
    assert Payslip.query.filter_by(company_id=company.id).count() == 0


def test_approval_stops_when_reviewed_rule_is_removed(app):
    from payroll_engine.services.payroll_service import process_payroll

    company = Company(name='Synthetic approval')
    db.session.add(company)
    db.session.flush()
    user = User(company_id=company.id, role='owner', phone='0910000102')
    user.set_password('Synthetic1!')
    db.session.add_all(
        [
            user,
            Employee(
                company_id=company.id, employee_id='TEST', name='Synthetic Worker', basic_salary=10000, allowances=0
            ),
        ]
    )
    rule = TaxRule(version_name='synthetic', effective_date=date(2020, 1, 1), status='active', rules_json=VALID)
    db.session.add(rule)
    db.session.commit()
    run = create_review(company.id, user.id, date(2026, 9, 1))
    db.session.commit()
    db.session.delete(rule)
    db.session.commit()
    invalidate_tax_cache()
    invalidate_pension_cache()
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
        session['active_company_id'] = company.id
    response = client.get(f'/payroll/{run.id}/confirm', follow_redirects=True)
    assert b'rule' in response.data.lower() and b'missing' in response.data.lower()
    result = process_payroll(run, company.id, user.id, 'owner@example.invalid', '127.0.0.1')
    assert not result.success
    assert 'rule' in result.message.lower() and 'missing' in result.message.lower()
    assert Payslip.query.filter_by(company_id=company.id).count() == 0


def test_valid_dated_rules_allow_payroll_approval(app, monkeypatch):
    from payroll_engine.services.payroll_service import process_payroll

    monkeypatch.setattr('payroll_engine.tasks.enqueue_batch', lambda *args, **kwargs: None)
    company = Company(name='Synthetic approved payroll')
    db.session.add(company)
    db.session.flush()
    user = User(company_id=company.id, role='owner', phone='0910000104')
    user.set_password('Synthetic1!')
    db.session.add_all(
        [
            user,
            Employee(
                company_id=company.id, employee_id='TEST', name='Synthetic Worker', basic_salary=10000, allowances=0
            ),
        ]
    )
    db.session.add(
        TaxRule(version_name='synthetic', effective_date=date(2020, 1, 1), status='active', rules_json=VALID)
    )
    db.session.commit()
    run = create_review(company.id, user.id, date(2026, 9, 1))
    db.session.commit()
    result = process_payroll(run, company.id, user.id, 'owner@example.invalid', '127.0.0.1')
    assert result.success, result.message or result.error
    slip = Payslip.query.filter_by(company_id=company.id, payroll_run_id=run.id).one()
    assert (slip.tax, slip.employee_pension, slip.employer_pension, slip.net_pay) == (
        Decimal('1650.00'),
        Decimal('700.00'),
        Decimal('1100.00'),
        Decimal('7650.00'),
    )


def test_excel_engine_rejects_absent_and_incomplete_rules(app):
    from payroll_engine.excel_payroll import ExcelPayrollEngine
    from payroll_engine.rule_errors import MissingPayrollRuleError

    with pytest.raises(MissingPayrollRuleError, match=r'tax.*missing'):
        ExcelPayrollEngine(for_date=date(2026, 9, 1))
    db.session.add(
        TaxRule(
            version_name='synthetic',
            effective_date=date(2020, 1, 1),
            status='active',
            rules_json=dict(VALID, pension={}),
        )
    )
    db.session.commit()
    with pytest.raises(MissingPayrollRuleError, match=r'pension.*incomplete'):
        ExcelPayrollEngine(for_date=date(2026, 9, 1))


def test_taxrule_pension_properties_do_not_default(app):
    from payroll_engine.rule_errors import MissingPayrollRuleError

    rule = TaxRule(version_name='synthetic', effective_date=date(2020, 1, 1), rules_json={'pension': {}})
    for field in ('pension_employee_rate', 'pension_employer_rate'):
        with pytest.raises(MissingPayrollRuleError, match=r'pension.*incomplete'):
            getattr(rule, field)


def test_historical_import_blocks_missing_pension_rule(app):
    company = Company(name='Synthetic import')
    db.session.add(company)
    db.session.flush()
    user = User(company_id=company.id, role='owner', phone='0910000103')
    user.set_password('Synthetic1!')
    db.session.add_all(
        [
            user,
            Employee(
                company_id=company.id, employee_id='TEST', name='Synthetic Worker', basic_salary=10000, allowances=0
            ),
        ]
    )
    db.session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
        session['active_company_id'] = company.id
    csv = b'employee_id,month,year,basic_salary,gross,tax,pension,net\nTEST,9,2026,10000,10000,1650,700,7650\n'
    response = client.post('/payroll/import', data={'file': (BytesIO(csv), 'synthetic.csv')}, follow_redirects=True)
    assert b'pension rule' in response.data.lower() and b'missing' in response.data.lower()
    assert Payslip.query.filter_by(company_id=company.id).count() == 0


def test_settlement_preview_shows_missing_rule_without_saving(app):
    from payroll_engine.models import FinalSettlement

    company = Company(name='Synthetic settlement')
    db.session.add(company)
    db.session.flush()
    user = User(company_id=company.id, role='owner', phone='0910000106')
    user.set_password('Synthetic1!')
    employee = Employee(
        company_id=company.id,
        employee_id='TEST',
        name='Synthetic Worker',
        basic_salary=10000,
        allowances=0,
        start_date=date(2024, 1, 1),
    )
    db.session.add_all([user, employee])
    db.session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
        session['active_company_id'] = company.id
    response = client.post(
        f'/employees/{employee.id}/terminate',
        data={'termination_reason': 'resignation', 'end_date': '2026-09-30', 'action': 'preview'},
    )
    assert response.status_code == 400
    assert b'rule' in response.data.lower() and b'missing' in response.data.lower()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0


def test_settlement_requires_rules_for_its_effective_date(app, monkeypatch):
    from payroll_engine.rule_errors import MissingPayrollRuleError
    from payroll_engine.services.settlement_service import calculate_settlement

    company = Company(name='Synthetic dated settlement')
    db.session.add(company)
    db.session.flush()
    employee = Employee(
        company_id=company.id,
        employee_id='TEST',
        name='Synthetic Worker',
        basic_salary=10000,
        allowances=0,
        start_date=date(2024, 1, 1),
    )
    db.session.add(employee)
    db.session.commit()
    current_rule = TaxRule(
        version_name='synthetic-current', effective_date=date(2026, 10, 1), status='active', rules_json=VALID
    )
    monkeypatch.setattr(TaxRule, 'get_active_rule', lambda for_date=None: current_rule if for_date is None else None)
    with pytest.raises(MissingPayrollRuleError, match='missing'):
        calculate_settlement(employee, 'resignation', date(2026, 9, 30), company.id, db.session)


def test_locked_payslip_remains_viewable_without_rule(app, monkeypatch):
    from pathlib import Path

    from payroll_engine.models import PayrollRun, PayslipGenerationJob
    from payroll_engine.pdf import _ensure_pdf
    from payroll_engine.tasks import generate_payslip_pdf

    company = Company(name='Synthetic historical payroll')
    db.session.add(company)
    db.session.flush()
    user = User(company_id=company.id, role='employee', phone='0910000105')
    user.set_password('Synthetic1!')
    db.session.add(user)
    db.session.flush()
    employee = Employee(
        company_id=company.id,
        user_id=user.id,
        employee_id='TEST',
        name='Synthetic Worker',
        basic_salary=10000,
        allowances=0,
    )
    run = PayrollRun(company_id=company.id, run_date=date(2026, 9, 1), status='locked')
    db.session.add_all([employee, run])
    db.session.flush()
    slip = Payslip(
        company_id=company.id,
        employee_id=employee.id,
        payroll_run_id=run.id,
        gross_salary=10000,
        tax=1650,
        employee_pension=700,
        employer_pension=1100,
        net_pay=7650,
        taxable_income=10000,
    )
    db.session.add(slip)
    db.session.commit()
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True
        session['active_company_id'] = company.id
    response = client.get(f'/my/payslips/{slip.id}')
    assert response.status_code == 200
    assert b'1650.00' in response.data and b'7650.00' in response.data
    assert b'tax breakdown is unavailable' in response.data.lower()
    path = _ensure_pdf(slip, employee)
    assert Path(path).is_file()
    slip.pdf_status = 'not_generated'
    slip.pdf_file_path = None
    job = PayslipGenerationJob(company_id=company.id, payslip_id=slip.id, batch_id='synthetic-batch')
    db.session.add(job)
    db.session.commit()
    job_id = job.id
    monkeypatch.setattr('payroll_engine.create_app', lambda: app)
    generate_payslip_pdf(job_id)
    db.session.expire_all()
    job = db.session.get(PayslipGenerationJob, job_id)
    assert job.status == 'generated', job.error_message
    slip = Payslip.query.filter_by(company_id=company.id, id=slip.id).one()
    assert Path(slip.pdf_file_path).is_file()
