"""Invented month inputs and literal, independently worked acceptance oracle."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

PERIOD = date(2026, 11, 1)
PASSWORD = 'Test1234!'
# basic, allowance, gross, tax, employee pension, employer pension, absence, net
CASES = (
    ('1800', '100', '1900', '0', '126', '198', '0', '1774'),
    ('3000', '200', '3200', '180', '210', '330', '0', '2810'),
    ('5000', '500', '5500', '600', '350', '550', '0', '4550'),
    ('8000', '1000', '9000', '1400', '560', '880', '0', '7040'),
    ('10000', '2000', '12000', '2250', '700', '1100', '0', '9050'),
    ('12000', '1000', '13000', '2550', '840', '1320', '866.67', '8743.33'),
    ('14000', '0', '14000', '2850', '980', '1540', '0', '10170'),
    ('16000', '2000', '18000', '4250', '1120', '1760', '0', '12630'),
    ('20800', '1000', '22400', '5790', '1456', '2288', '0', '15154'),
    ('25000.50', '1500.25', '26500.75', '7225.26', '1750.04', '2750.06', '0', '17525.45'),
)
FIELDS = ('gross_salary', 'tax', 'employee_pension', 'employer_pension', 'unpaid_leave_reduction', 'net_pay')


def money(value):
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class Inputs(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.values = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'input' and values.get('name'):
            self.values[values['name']] = values.get('value', '')


def make_app(uri, upload_dir, *, migrated=False):
    import config
    from payroll_engine import create_app, db

    config.TestingConfig.SQLALCHEMY_DATABASE_URI = uri
    app = create_app()
    app.config.update(WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False, UPLOAD_FOLDER=str(upload_dir))
    with app.app_context():
        if migrated:
            from flask_migrate import upgrade

            upgrade(directory=str(Path(__file__).resolve().parents[1] / 'migrations'))
        else:
            db.create_all()
    return app


def seed_month(app):
    from payroll_engine import db
    from payroll_engine.models import Company, Employee, TaxRule, User, UserCompany

    with app.app_context():
        db.session.add(
            TaxRule(
                version_name='SYNTHETIC-month-2025-schedule',
                effective_date=PERIOD,
                status='active',
                rules_json={
                    'brackets': [
                        {'max': 2000, 'rate': '0'},
                        {'max': 4000, 'rate': '0.15'},
                        {'max': 7000, 'rate': '0.20'},
                        {'max': 10000, 'rate': '0.25'},
                        {'max': 14000, 'rate': '0.30'},
                        {'max': None, 'rate': '0.35'},
                    ],
                    'pension': {'employee_rate': '0.07', 'employer_rate': '0.11'},
                },
            )
        )
        company = Company(name='Imaginary Lantern QA PLC', country='ET', currency='ETB')
        db.session.add(company)
        db.session.flush()
        owner = User(company_id=company.id, email='synthetic-owner@example.invalid', role='owner')
        owner.set_password(PASSWORD)
        db.session.add(owner)
        db.session.flush()
        db.session.add(UserCompany(user_id=owner.id, company_id=company.id, role='owner'))
        employees = []
        for index, case in enumerate(CASES, 1):
            employee = Employee(
                company_id=company.id,
                employee_id=f'SYN{index:02}',
                name=f'Invented QA Person {index:02}',
                basic_salary=money(case[0]),
                allowances=money(case[1]),
                employee_type='monthly',
                tin=f'SYNTHETIC-TIN-{index:02}',
                bank_account=f'SYNTHETIC-BANK-{index:02}',
                fayda_fin=f'SYNTHETIC-FIN-{index:02}',
            )
            db.session.add(employee)
            employees.append(employee)
        db.session.commit()
        return company.id, owner.id, [employee.id for employee in employees]


def client_for(app, company_id, user_id):
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
        session['active_company_id'] = company_id
    return client


def assert_payslips(app, company_id, run_id):
    from payroll_engine import db
    from payroll_engine.models import Employee, Payslip

    with app.app_context():
        rows = (
            db.session.query(Payslip, Employee.employee_id)
            .join(Employee)
            .filter(
                Payslip.company_id == company_id,
                Payslip.payroll_run_id == run_id,
                Employee.company_id == company_id,
            )
            .order_by(Employee.employee_id)
            .all()
        )
        assert len(rows) == len(CASES)
        for (payslip, code), case in zip(rows, CASES, strict=True):
            for field, expected in zip(FIELDS, case[2:], strict=True):
                actual = getattr(payslip, field)
                assert actual == money(expected), f'{code} {field}: app={actual}, hand={expected}'
        totals = {}
        for offset, field in enumerate(FIELDS, 2):
            actual = sum((getattr(ps, field) for ps, _ in rows), Decimal('0'))
            expected = sum((money(case[offset]) for case in CASES), Decimal('0'))
            assert actual == expected, f'run {field}: app={actual}, hand={expected}'
            totals[field] = str(actual)
        return totals


class MonthDate(date):
    @classmethod
    def today(cls):
        return PERIOD


@patch('payroll_engine.payroll_bp.date', MonthDate)
def complete_month(app):
    from payroll_engine import db
    from payroll_engine.models import PayrollDraft, PayrollRun, Payslip

    company_id, user_id, employees = seed_month(app)
    client = client_for(app, company_id, user_id)
    data = {'period_start': PERIOD.isoformat(), 'action': 'calculate', 'emp_id': [str(e) for e in employees]}
    for index, employee_id in enumerate(employees, 1):
        for key in ('ot_day', 'ot_night', 'ot_holiday', 'ot_rest', 'absences', 'advance', 'bonus'):
            data[f'emp_{employee_id}_{key}'] = '0'
        if index == 6:
            data[f'emp_{employee_id}_absences'] = '2'
        if index == 9:
            data[f'emp_{employee_id}_ot_day'] = '4'
    response = client.post('/payroll/spreadsheet', data=data)
    assert response.status_code == 302, response.get_data(as_text=True)
    response = client.post('/payroll/spreadsheet/review', data={'period_start': PERIOD.isoformat()})
    assert response.status_code == 302, response.get_data(as_text=True)
    with app.app_context():
        run = PayrollRun.query.filter_by(company_id=company_id, source='spreadsheet').one()
        run_id = run.id
        assert run.status == 'review'
        draft = PayrollDraft.query.filter_by(company_id=company_id, payroll_run_id=run_id).one()
        assert len(draft.employee_data) == 10
        for row, case in zip(sorted(draft.employee_data, key=lambda r: r['id']), CASES, strict=True):
            for field, expected in zip(
                ('gross', 'tax', 'pension_employee', 'pension_employer', 'unpaid_leave_reduction', 'net'),
                case[2:],
                strict=True,
            ):
                assert money(row[field]) == money(expected), f'review {row["id"]} {field}: {row[field]} != {expected}'
        assert Payslip.query.filter_by(company_id=company_id, payroll_run_id=run_id).count() == 0
    assert client.get(f'/payroll/runs/{run_id}/review').status_code == 200
    assert client.post(f'/payroll/runs/{run_id}/submit').status_code == 302
    confirmation = client.get(f'/payroll/{run_id}/confirm')
    assert confirmation.status_code == 200
    inputs = Inputs(confirmation.get_data(as_text=True)).values
    approval = {key: inputs[key] for key in ('run_id', 'run_version', 'idempotency_key')}
    approval['password'] = PASSWORD
    assert client.post('/payroll/approve', data=approval).status_code == 302
    totals = assert_payslips(app, company_id, run_id)
    replay = client.post('/payroll/approve', data=approval)
    assert replay.headers.get('Idempotent-Replay') == 'true'
    assert assert_payslips(app, company_id, run_id) == totals
    with app.app_context():
        run = db.session.get(PayrollRun, run_id)
        assert run.status == 'completed' and run.approved_by == user_id and run.approved_at
        assert run.disbursement_status == 'pending'
    assert client.post(f'/payroll/runs/{run_id}/lock').status_code == 302
    with app.app_context():
        assert db.session.get(PayrollRun, run_id).status == 'locked'
    return company_id, user_id, run_id, totals
