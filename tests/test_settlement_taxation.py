"""Final settlement taxation (PLAN.md R2, R3).

Severance, pay in lieu of notice and leave encashment are employment income
(Proc. 979/2016 Art. 12(1)(c); rates per Proc. 1395/2025). They are added to
the final month's taxable income and taxed once with the monthly brackets.
No leave record means no leave paid, plus a warning.

Worked examples, by hand (brackets 0 / 15 / 20 / 25 / 30 / 35 % at
2,000 / 4,000 / 7,000 / 10,000 / 14,000; tax over 14,000 = 35 % x T - 2,050):

Employee: basic 10,000, allowances 0, hired 2024-07-31, last day 2026-07-31
(full month, so outstanding salary = 10,000; pension 7 % = 700).
Years of service: 730 / 365.25 = 1.9986 -> 2.00.
Severance (redundancy): 30 + 30 x 0.333 x 1 = 39.99 days x 10,000/30
  = 13,330.00.
Leave record: entitled 16, taken 6 -> 10 days x 333.333... = 3,333.33.

A) Pension deducted before tax (PENSION_DEDUCTED_BEFORE_TAX = True, current):
   taxable = 10,000 - 700 + 13,330 + 3,333.33 = 25,963.33
   tax     = 0.35 x 25,963.33 - 2,050 = 7,037.1655 -> 7,037.17
   salary-only tax on 9,300 = 300 + 600 + 0.25 x 2,300 = 1,475.00
   tax from lump sums = 7,037.17 - 1,475.00 = 5,562.17
   net = 10,000 + 13,330 + 3,333.33 - 700 - 7,037.17 = 18,926.16
B) Pension not deducted before tax (flag False, R1 fix):
   taxable = 26,663.33; tax = 0.35 x 26,663.33 - 2,050 = 7,282.1655 -> 7,282.17
   net = 26,663.33 - 700 - 7,282.17 = 18,681.16
C) Resignation, no leave record, 5 manual leave days, notice pay 5,000 (flag True):
   leave = 5 x 333.333... = 1,666.67
   taxable = 9,300 + 5,000 + 1,666.67 = 15,966.67
   tax = 0.35 x 15,966.67 - 2,050 = 3,538.3345 -> 3,538.33
   net = 10,000 + 5,000 + 1,666.67 - 700 - 3,538.33 = 12,428.34
D) Resignation, no leave record, nothing entered: leave 0, warning;
   tax = 1,475.00, net = 10,000 - 700 - 1,475 = 7,825.00
"""

from datetime import date
from decimal import Decimal

import pytest

from payroll_engine import constants, create_app, db
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    EmployeeDeduction,
    FinalSettlement,
    LeaveBalance,
    TenantQuery,
    User,
)
from payroll_engine.services import settlement_service
from payroll_engine.services.settlement_service import (
    NO_LEAVE_RECORD_WARNING,
    calculate_settlement,
    create_settlement_record,
)
from payroll_engine.severance import TerminationReason

START = date(2024, 7, 31)
END = date(2026, 7, 31)


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        for model in [Employee, EmployeeDeduction, LeaveBalance, FinalSettlement, AuditLog]:
            TenantQuery.register_model(model)
        yield app
        db.drop_all()


@pytest.fixture
def setup(app):
    company = Company(name='Synthetic Settlement Co')
    db.session.add(company)
    db.session.flush()
    user = User(phone='911000777', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    emp = Employee(
        employee_id='SYN-1',
        name='Synthetic Worker',
        basic_salary=Decimal('10000'),
        allowances=Decimal('0'),
        company_id=company.id,
        start_date=START,
    )
    db.session.add(emp)
    db.session.commit()
    return company, user, emp


def _add_leave(company, emp, entitled=16, taken=6, year=2026):
    db.session.add(
        LeaveBalance(
            company_id=company.id, employee_id=emp.id, leave_type='annual', year=year, entitled=entitled, taken=taken
        )
    )
    db.session.commit()


def test_example_a_pension_before_tax(setup, monkeypatch):
    monkeypatch.setattr(constants, 'PENSION_DEDUCTED_BEFORE_TAX', True)
    company, _, emp = setup
    _add_leave(company, emp)
    r = calculate_settlement(emp, TerminationReason.REDUNDANCY, END, company.id, db.session)
    assert r['outstanding_salary'] == Decimal('10000')
    assert r['severance_amount'] == Decimal('13330.00')
    assert r['unused_leave_days'] == Decimal('10')
    assert r['leave_days_source'] == 'leave_record'
    assert r['leave_encashment'] == Decimal('3333.33')
    assert r['pension_deduction'] == Decimal('700.00')
    assert r['taxable_income'] == Decimal('25963.33')
    assert r['tax_salary_only'] == Decimal('1475.00')
    assert r['income_tax'] == Decimal('7037.17')
    assert r['tax_on_salary'] == r['income_tax']
    assert r['tax_on_termination_payments'] == Decimal('5562.17')
    assert r['net_final_payment'] == Decimal('18926.16')
    assert r['warnings'] == []


def test_example_b_pension_not_before_tax(setup, monkeypatch):
    monkeypatch.setattr(constants, 'PENSION_DEDUCTED_BEFORE_TAX', False)
    company, _, emp = setup
    _add_leave(company, emp)
    r = calculate_settlement(emp, TerminationReason.REDUNDANCY, END, company.id, db.session)
    assert r['taxable_income'] == Decimal('26663.33')
    assert r['income_tax'] == Decimal('7282.17')
    assert r['net_final_payment'] == Decimal('18681.16')
    assert r['calculation_details']['pension_deducted_before_tax'] is False


def test_example_c_manual_leave_and_notice_pay(setup, monkeypatch):
    monkeypatch.setattr(constants, 'PENSION_DEDUCTED_BEFORE_TAX', True)
    company, _, emp = setup
    r = calculate_settlement(
        emp,
        TerminationReason.RESIGNATION,
        END,
        company.id,
        db.session,
        unused_leave_days=Decimal('5'),
        notice_pay=Decimal('5000'),
    )
    assert r['severance_amount'] == Decimal('0')
    assert r['notice_pay'] == Decimal('5000.00')
    assert r['leave_days_source'] == 'manual'
    assert r['leave_encashment'] == Decimal('1666.67')
    assert r['taxable_income'] == Decimal('15966.67')
    assert r['income_tax'] == Decimal('3538.33')
    assert r['net_final_payment'] == Decimal('12428.34')
    assert r['warnings'] == []


def test_example_d_missing_leave_record(setup, monkeypatch):
    monkeypatch.setattr(constants, 'PENSION_DEDUCTED_BEFORE_TAX', True)
    company, _, emp = setup
    r = calculate_settlement(emp, TerminationReason.RESIGNATION, END, company.id, db.session)
    assert r['unused_leave_days'] == Decimal('0')
    assert r['leave_encashment'] == Decimal('0.00')
    assert r['leave_days_source'] == 'none'
    assert r['warnings'] == [NO_LEAVE_RECORD_WARNING]
    assert NO_LEAVE_RECORD_WARNING == 'No leave records — enter unused leave days manually'
    assert r['income_tax'] == Decimal('1475.00')
    assert r['net_final_payment'] == Decimal('7825.00')


def test_manual_days_override_record_with_warning(setup):
    company, _, emp = setup
    _add_leave(company, emp)  # 10 days on record
    r = calculate_settlement(emp, TerminationReason.RESIGNATION, END, company.id, db.session, unused_leave_days=4)
    assert r['unused_leave_days'] == Decimal('4')
    assert r['leave_encashment'] == Decimal('1333.33')
    assert any('differs from the leave record' in w for w in r['warnings'])


def test_negative_inputs_rejected(setup):
    company, _, emp = setup
    with pytest.raises(ValueError):
        calculate_settlement(emp, TerminationReason.RESIGNATION, END, company.id, db.session, unused_leave_days=-1)
    with pytest.raises(ValueError):
        calculate_settlement(emp, TerminationReason.RESIGNATION, END, company.id, db.session, notice_pay='-5')


def test_unknown_tax_method_refused(setup, monkeypatch):
    company, _, emp = setup
    monkeypatch.setattr(settlement_service, 'SETTLEMENT_LUMP_SUM_TAX_METHOD', 'spread_over_years')
    with pytest.raises(ValueError):
        calculate_settlement(emp, TerminationReason.RESIGNATION, END, company.id, db.session)


def test_all_money_is_decimal(setup):
    company, _, emp = setup
    _add_leave(company, emp)
    r = calculate_settlement(emp, TerminationReason.REDUNDANCY, END, company.id, db.session, notice_pay='1234.5')
    for key in (
        'severance_amount',
        'outstanding_salary',
        'notice_pay',
        'leave_encashment',
        'pension_deduction',
        'taxable_income',
        'income_tax',
        'tax_salary_only',
        'tax_on_termination_payments',
        'total_earnings',
        'total_deductions',
        'net_final_payment',
    ):
        assert isinstance(r[key], Decimal), key
    assert r['total_earnings'] == (
        r['outstanding_salary'] + r['severance_amount'] + r['notice_pay'] + r['leave_encashment']
    )


def test_persisted_record_keeps_taxable_lines(setup, monkeypatch):
    monkeypatch.setattr(constants, 'PENSION_DEDUCTED_BEFORE_TAX', True)
    company, user, emp = setup
    _add_leave(company, emp)
    s = create_settlement_record(emp, TerminationReason.REDUNDANCY, END, company.id, user.id, db.session)
    db.session.commit()
    saved = db.session.get(FinalSettlement, s.id)
    assert saved.tax_on_salary == Decimal('7037.17')
    assert saved.taxable_income == Decimal('25963.33')
    assert saved.notice_pay == Decimal('0.00')
    lines = {line['code']: line['amount'] for line in saved.calculation_details['taxable_lines']}
    assert lines == {
        'outstanding_salary': '10000.00',
        'severance': '13330.00',
        'notice_pay': '0.00',
        'leave_encashment': '3333.33',
    }
    assert saved.calculation_details['tax_method'] == 'final_month_aggregate'


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def test_terminate_route_no_leave_record_warns_and_shows_tax(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)

    page = client.get(f'/employees/{emp.id}/terminate')
    assert page.status_code == 200
    assert 'No leave records — enter unused leave days manually' in page.get_data(as_text=True)

    resp = client.post(
        f'/employees/{emp.id}/terminate',
        data={'termination_reason': 'redundancy', 'password': 'Test1234!', 'end_date': END.isoformat()},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    settlement = FinalSettlement.query.filter_by(company_id=company.id, employee_id=emp.id).one()
    assert settlement.leave_encashment == Decimal('0.00')
    assert 'No leave records — enter unused leave days manually' in html
    assert 'Total income tax' in html
    assert 'Severance Pay' in html


def test_terminate_route_manual_inputs(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    resp = client.post(
        f'/employees/{emp.id}/terminate',
        data={
            'termination_reason': 'resignation',
            'password': 'Test1234!',
            'end_date': END.isoformat(),
            'unused_leave_days': '5',
            'notice_pay': '5,000',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    settlement = FinalSettlement.query.filter_by(company_id=company.id, employee_id=emp.id).one()
    assert settlement.notice_pay == Decimal('5000.00')
    assert settlement.leave_encashment == Decimal('1666.67')
    assert 'Pay in lieu of notice' in resp.get_data(as_text=True)


def test_terminate_route_rejects_bad_leave_days(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    client.post(
        f'/employees/{emp.id}/terminate',
        data={
            'termination_reason': 'resignation',
            'password': 'Test1234!',
            'end_date': END.isoformat(),
            'unused_leave_days': '-3',
        },
    )
    assert FinalSettlement.query.filter_by(company_id=company.id, employee_id=emp.id).count() == 0
