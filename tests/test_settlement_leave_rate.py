"""Leave encashment daily-rate basis: a per-company setting.

Worked examples, by hand:

Employee: basic 10,000; regular monthly allowance (transport) 2,000 on record;
10 unused leave days (entered manually).

- basic_plus_regular_allowances (default, the previous behaviour):
    daily rate = (10,000 + 2,000) / 30 = 400.00; 10 x 400 = 4,000.00
- basic_only:
    daily rate = 10,000 / 30 = 333.333...; 10 x 333.333... = 3,333.33
- basic_only with divisor 26:
    daily rate = 10,000 / 26 = 384.615384...; x 10 = 3,846.153846... -> 3,846.15
- basic_plus_regular_allowances with divisor 26:
    12,000 / 26 x 10 = 4,615.384615... -> 4,615.38

The daily rate stays unrounded; only the encashment is rounded once.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

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
from payroll_engine.services.settlement_service import (
    calculate_settlement,
    company_leave_rate_settings,
    create_settlement_record,
    leave_daily_rate,
    validate_leave_rate_settings,
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
    # The company has confirmed its leave-pay basis and divisor, so settlements
    # with leave encashment can be finalized (see test_settlement_leave_rule_confirmation.py
    # for the unconfirmed block).
    company = Company(name='Synthetic Leave Rate Co', leave_rate_confirmed_at=datetime(2026, 10, 25, 9, 0))
    db.session.add(company)
    db.session.flush()
    user = User(phone='911000778', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    emp = Employee(
        employee_id='SYN-LR-1',
        name='Synthetic Leave Worker',
        basic_salary=Decimal('10000'),
        allowances=Decimal('2000'),  # regular monthly transport allowance
        company_id=company.id,
        start_date=START,
    )
    db.session.add(emp)
    db.session.commit()
    return company, user, emp


def _settle(company, emp, **kw):
    return calculate_settlement(
        emp, TerminationReason.RESIGNATION, END, company.id, db.session, unused_leave_days=Decimal('10'), **kw
    )


def test_new_company_defaults_keep_previous_behaviour(setup):
    company, _, emp = setup
    db.session.refresh(company)
    assert company.leave_rate_basis == 'basic_plus_regular_allowances'
    assert company.leave_rate_divisor == 30
    assert constants.DEFAULT_LEAVE_RATE_BASIS == 'basic_plus_regular_allowances'
    assert constants.DEFAULT_LEAVE_RATE_DIVISOR == 30
    assert company_leave_rate_settings(company.id, db.session) == ('basic_plus_regular_allowances', 30)
    assert company_leave_rate_settings(company.id, None) == ('basic_plus_regular_allowances', 30)

    r = _settle(company, emp)
    assert r['leave_encashment'] == Decimal('4000.00')
    # Unchanged helper default: (basic + allowances) / 30, unrounded.
    assert leave_daily_rate(emp) == Decimal('12000') / Decimal('30')


def test_basic_plus_regular_allowances_example(setup):
    company, _, emp = setup
    r = _settle(company, emp)
    assert r['leave_encashment'] == Decimal('4000.00')
    leave = r['calculation_details']['leave']
    assert leave['rate_basis'] == 'basic_plus_regular_allowances'
    assert leave['rate_basis_label'] == 'Basic + allowances that qualify as wages (Art. 53)'
    assert leave['rate_divisor'] == 30
    assert leave['rate_monthly_base'] == '12000.00'
    assert leave['daily_rate'] == '400.00'
    assert leave['rate_components'] == [
        {'code': 'basic_salary', 'label': 'Basic salary', 'amount': '10000.00', 'included': True},
        {'code': 'regular_allowances', 'label': 'Regular allowances', 'amount': '2000.00', 'included': True},
    ]


def test_basic_only_example(setup):
    company, _, emp = setup
    company.leave_rate_basis = 'basic_only'
    db.session.commit()
    r = _settle(company, emp)
    assert r['leave_encashment'] == Decimal('3333.33')
    leave = r['calculation_details']['leave']
    assert leave['rate_basis'] == 'basic_only'
    assert leave['rate_monthly_base'] == '10000.00'
    assert leave['daily_rate'] == '333.33'
    assert leave['daily_rate_unrounded'] == '333.333333'
    assert leave['rate_components'][1] == {
        'code': 'regular_allowances',
        'label': 'Regular allowances',
        'amount': '2000.00',
        'included': False,
    }
    # Everything else (salary, tax base) still sees the allowances.
    assert r['outstanding_salary'] == Decimal('12000')
    assert r['total_earnings'] == Decimal('12000') + Decimal('3333.33')


def test_divisor_is_configurable(setup):
    company, _, emp = setup
    company.leave_rate_basis = 'basic_only'
    company.leave_rate_divisor = 26
    db.session.commit()
    r = _settle(company, emp)
    assert r['leave_encashment'] == Decimal('3846.15')
    assert r['calculation_details']['leave']['rate_divisor'] == 26

    company.leave_rate_basis = 'basic_plus_regular_allowances'
    db.session.commit()
    assert _settle(company, emp)['leave_encashment'] == Decimal('4615.38')


def test_explicit_override_beats_company_setting(setup):
    company, _, emp = setup
    company.leave_rate_basis = 'basic_only'
    db.session.commit()
    r = _settle(company, emp, leave_rate_basis='basic_plus_regular_allowances')
    assert r['leave_encashment'] == Decimal('4000.00')


def test_persisted_settlement_freezes_basis(setup):
    company, user, emp = setup
    company.leave_rate_basis = 'basic_only'
    db.session.commit()
    s = create_settlement_record(
        emp, TerminationReason.RESIGNATION, END, company.id, user.id, db.session, unused_leave_days=10
    )
    db.session.commit()
    # Changing the setting later does not touch a saved settlement.
    company.leave_rate_basis = 'basic_plus_regular_allowances'
    db.session.commit()
    saved = db.session.get(FinalSettlement, s.id)
    assert saved.leave_encashment == Decimal('3333.33')
    assert saved.calculation_details['leave']['rate_basis'] == 'basic_only'
    assert saved.calculation_details['leave']['rate_divisor'] == 30


def test_validation_rejects_bad_settings():
    assert validate_leave_rate_settings('basic_only', '26') == ('basic_only', 26)
    for basis, divisor in [
        ('gross', 30),
        ('basic_only', 0),
        ('basic_only', 32),
        ('basic_only', '30.5'),
        ('basic_only', 'abc'),
        ('basic_only', None),
    ]:
        with pytest.raises(ValueError):
            validate_leave_rate_settings(basis, divisor)


def test_database_refuses_unknown_basis(setup):
    company, _, _ = setup
    company.leave_rate_basis = 'gross'
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    company = db.session.get(Company, company.id)
    company.leave_rate_divisor = 0
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def test_company_settings_page_saves_setting_and_audits(app, setup):
    company, user, _ = setup
    client = app.test_client()
    _login(client, user)

    page = client.get('/settings/company')
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert 'name="leave_rate_basis"' in html
    assert 'Basic + allowances that qualify as wages (Art. 53)' in html
    assert '(default)' not in html
    assert 'name="leave_rate_divisor"' in html

    resp = client.post(
        '/settings/company',
        data={'name': company.name, 'leave_rate_basis': 'basic_only', 'leave_rate_divisor': '26'},
    )
    assert resp.status_code == 302
    db.session.expire_all()
    saved = db.session.get(Company, company.id)
    assert (saved.leave_rate_basis, saved.leave_rate_divisor) == ('basic_only', 26)
    log = AuditLog.query.filter_by(company_id=company.id, action='leave_rate_setting_change').one()
    assert log.details['leave_rate_basis'] == {'old': 'basic_plus_regular_allowances', 'new': 'basic_only'}
    assert log.details['leave_rate_divisor'] == {'old': 30, 'new': 26}


def test_company_settings_rejects_bad_values_and_keeps_old(app, setup):
    company, user, _ = setup
    client = app.test_client()
    _login(client, user)
    for data in ({'leave_rate_basis': 'gross'}, {'leave_rate_basis': 'basic_only', 'leave_rate_divisor': '0'}):
        client.post('/settings/company', data={'name': 'Renamed', **data})
        db.session.expire_all()
        saved = db.session.get(Company, company.id)
        assert (saved.leave_rate_basis, saved.leave_rate_divisor) == ('basic_plus_regular_allowances', 30)
        assert saved.name == 'Synthetic Leave Rate Co'


def test_company_settings_without_fields_keeps_setting(app, setup):
    company, user, _ = setup
    company.leave_rate_basis = 'basic_only'
    db.session.commit()
    client = app.test_client()
    _login(client, user)
    client.post('/settings/company', data={'name': company.name})
    db.session.expire_all()
    assert db.session.get(Company, company.id).leave_rate_basis == 'basic_only'


def test_settlement_detail_page_shows_basis(app, setup):
    company, user, emp = setup
    company.leave_rate_basis = 'basic_only'
    db.session.commit()
    client = app.test_client()
    _login(client, user)
    resp = client.post(
        f'/employees/{emp.id}/terminate',
        data={
            'termination_reason': 'resignation',
            'password': 'Test1234!',
            'end_date': END.isoformat(),
            'unused_leave_days': '10',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    settlement = FinalSettlement.query.filter_by(company_id=company.id, employee_id=emp.id).one()
    assert settlement.leave_encashment == Decimal('3333.33')
    assert 'data-testid="leave-rate-basis"' in html
    assert 'Daily rate basis: Basic salary only' in html
    assert '÷ 30 days' in html
    assert 'ETB 333.33/day' in html
    assert 'regular allowances ETB 2000.00 not included' in html
    # Changing the basis directly in the DB keeps the confirmation stamp,
    # so the settlement is finalized and shows no leave-pay pending notice.
    assert 'data-testid="settlement-pending-confirmation"' not in html
    assert 'data-testid="settlement-tax-method"' in html
    assert 'statutory default: aggregated in month received (Proc. 979/2016 Arts 10, 12, 88)' in html
