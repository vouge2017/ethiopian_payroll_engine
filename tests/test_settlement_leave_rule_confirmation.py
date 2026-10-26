"""Leave-pay rule must be confirmed by the company before a settlement with
leave encashment can be finalized.

Adviser 2026-10-25 (Q3 PARTIAL): leave pay uses qualifying wages under Labour
Proc. 1156/2019 Arts 53 and 77; no universal divisor is established; "a
configurable divisor is a software feature, not legal approval. Do not use an
unconfirmed default for live settlements."

Worked example (hand-checked): basic 10,000, allowance 2,000 on record,
10 unused days, default basis (basic + qualifying allowances) / 30
-> 12,000 / 30 x 10 = 4,000.00 leave encashment.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from payroll_engine import create_app, db
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
    LEAVE_RULE_BLOCK_MESSAGE,
    LEAVE_RULE_PENDING_NOTICE,
    LeaveRuleNotConfirmedError,
    calculate_settlement,
    company_leave_rule_confirmation,
    create_settlement_record,
    settlement_finalize_block,
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
    company = Company(name='Synthetic Unconfirmed Co')  # leave rule NOT confirmed
    db.session.add(company)
    db.session.flush()
    user = User(phone='911000779', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    emp = Employee(
        employee_id='SYN-LC-1',
        name='Synthetic Confirm Worker',
        basic_salary=Decimal('10000'),
        allowances=Decimal('2000'),
        company_id=company.id,
        start_date=START,
    )
    db.session.add(emp)
    db.session.commit()
    return company, user, emp


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def _confirm(company):
    company.leave_rate_confirmed_at = datetime(2026, 10, 25, 9, 0)
    db.session.commit()


# --- service --------------------------------------------------------------


def test_new_company_is_unconfirmed(setup):
    company, _, _ = setup
    state = company_leave_rule_confirmation(company.id, db.session)
    assert state['confirmed'] is False
    assert (state['basis'], state['divisor']) == ('basic_plus_regular_allowances', 30)
    assert company_leave_rule_confirmation(company.id, None)['confirmed'] is False


def test_unconfirmed_preview_computes_with_warning_but_cannot_finalize(setup):
    company, user, emp = setup
    r = calculate_settlement(emp, TerminationReason.RESIGNATION, END, company.id, db.session, unused_leave_days=10)
    assert r['leave_encashment'] == Decimal('4000.00')
    details = r['calculation_details']
    assert details['leave']['rule_confirmed'] is False
    assert details['pending_confirmation'] == LEAVE_RULE_PENDING_NOTICE
    assert any(LEAVE_RULE_BLOCK_MESSAGE in w for w in r['warnings'])
    assert settlement_finalize_block(r) == LEAVE_RULE_BLOCK_MESSAGE

    with pytest.raises(LeaveRuleNotConfirmedError) as exc:
        create_settlement_record(
            emp, TerminationReason.RESIGNATION, END, company.id, user.id, db.session, unused_leave_days=10
        )
    assert str(exc.value) == LEAVE_RULE_BLOCK_MESSAGE
    db.session.commit()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0


def test_unconfirmed_without_leave_pay_can_finalize(setup):
    company, user, emp = setup
    s = create_settlement_record(emp, TerminationReason.RESIGNATION, END, company.id, user.id, db.session)
    db.session.commit()
    assert s.leave_encashment == Decimal('0.00')
    # Still flagged as pending, but nothing leave-related is paid, so no block.
    assert s.calculation_details['pending_confirmation'] == LEAVE_RULE_PENDING_NOTICE
    assert not any(LEAVE_RULE_BLOCK_MESSAGE in w for w in s.calculation_details['warnings'])


def test_confirmed_company_finalizes_without_pending_notice(setup):
    company, user, emp = setup
    _confirm(company)
    s = create_settlement_record(
        emp, TerminationReason.RESIGNATION, END, company.id, user.id, db.session, unused_leave_days=10
    )
    db.session.commit()
    assert s.leave_encashment == Decimal('4000.00')
    assert s.calculation_details['pending_confirmation'] is None
    assert s.calculation_details['leave']['rule_confirmed'] is True
    assert s.calculation_details['leave']['rule_confirmed_at'] == '2026-10-25T09:00:00'


def test_override_basis_differs_from_confirmed_is_not_confirmed(setup):
    company, _, emp = setup
    _confirm(company)
    r = calculate_settlement(
        emp,
        TerminationReason.RESIGNATION,
        END,
        company.id,
        db.session,
        unused_leave_days=10,
        leave_rate_basis='basic_only',
    )
    assert r['calculation_details']['leave']['rule_confirmed'] is False
    assert settlement_finalize_block(r) == LEAVE_RULE_BLOCK_MESSAGE


# --- routes ---------------------------------------------------------------


def test_terminate_blocked_when_unconfirmed(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    page = client.get(f'/employees/{emp.id}/terminate')
    assert 'data-testid="leave-rule-unconfirmed-warning"' in page.get_data(as_text=True)

    resp = client.post(
        f'/employees/{emp.id}/terminate',
        data={
            'termination_reason': 'resignation',
            'password': 'Test1234!',
            'end_date': END.isoformat(),
            'unused_leave_days': '10',
        },
    )
    assert resp.status_code == 409
    html = resp.get_data(as_text=True)
    assert 'data-testid="settlement-finalize-blocked"' in html
    assert LEAVE_RULE_BLOCK_MESSAGE in html
    assert '/settings/company#leave-pay-rule' in html
    assert 'data-testid="settlement-preview"' in html
    assert 'ETB 4000.00' in html
    assert 'value="10.00"' in html or 'value="10"' in html  # input kept
    db.session.expire_all()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0
    assert db.session.get(Employee, emp.id).is_deleted is False


def test_preview_without_password_saves_nothing(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    resp = client.post(
        f'/employees/{emp.id}/terminate',
        data={
            'action': 'preview',
            'termination_reason': 'resignation',
            'end_date': END.isoformat(),
            'unused_leave_days': '10',
        },
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'data-testid="settlement-preview"' in html
    assert 'Not saved' in html
    assert 'ETB 4000.00' in html
    assert LEAVE_RULE_BLOCK_MESSAGE in html  # visible warning
    assert 'data-testid="settlement-finalize-blocked"' not in html
    db.session.expire_all()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0
    assert db.session.get(Employee, emp.id).is_deleted is False


def test_terminate_without_leave_pay_allowed_when_unconfirmed(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    resp = client.post(
        f'/employees/{emp.id}/terminate',
        data={'termination_reason': 'resignation', 'password': 'Test1234!', 'end_date': END.isoformat()},
    )
    assert resp.status_code == 302
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 1


def test_confirm_in_settings_then_terminate_allowed(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    page = client.get('/settings/company').get_data(as_text=True)
    assert 'data-testid="leave-rule-unconfirmed"' in page
    assert 'name="leave_rate_confirm"' in page

    resp = client.post(
        '/settings/company',
        data={
            'name': company.name,
            'leave_rate_basis': 'basic_plus_regular_allowances',
            'leave_rate_divisor': '30',
            'leave_rate_confirm': '1',
        },
    )
    assert resp.status_code == 302
    db.session.expire_all()
    saved = db.session.get(Company, company.id)
    assert saved.leave_rate_confirmed_at is not None
    assert saved.leave_rate_confirmed_by == user.id
    log = AuditLog.query.filter_by(company_id=company.id, action='leave_rate_confirmation_change').one()
    assert log.details['confirmed'] is True
    assert log.details['leave_rate_basis'] == 'basic_plus_regular_allowances'
    assert log.details['leave_rate_divisor'] == 30
    assert 'data-testid="leave-rule-confirmed"' in client.get('/settings/company').get_data(as_text=True)

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
    settlement = FinalSettlement.query.filter_by(company_id=company.id, employee_id=emp.id).one()
    assert settlement.leave_encashment == Decimal('4000.00')
    assert settlement.calculation_details['leave']['rule_confirmed'] is True
    assert 'data-testid="settlement-pending-confirmation"' not in resp.get_data(as_text=True)


def test_changing_rule_without_reconfirming_clears_confirmation(app, setup):
    company, user, _ = setup
    _confirm(company)
    client = app.test_client()
    _login(client, user)
    client.post(
        '/settings/company',
        data={'name': company.name, 'leave_rate_basis': 'basic_only', 'leave_rate_divisor': '26'},
    )
    db.session.expire_all()
    saved = db.session.get(Company, company.id)
    assert (saved.leave_rate_basis, saved.leave_rate_divisor) == ('basic_only', 26)
    assert saved.leave_rate_confirmed_at is None
    log = AuditLog.query.filter_by(company_id=company.id, action='leave_rate_confirmation_change').one()
    assert log.details['confirmed'] is False


def test_resaving_confirmed_rule_keeps_original_stamp(app, setup):
    company, user, _ = setup
    _confirm(company)
    client = app.test_client()
    _login(client, user)
    client.post(
        '/settings/company',
        data={
            'name': 'Renamed Co',
            'leave_rate_basis': 'basic_plus_regular_allowances',
            'leave_rate_divisor': '30',
            'leave_rate_confirm': '1',
        },
    )
    db.session.expire_all()
    saved = db.session.get(Company, company.id)
    assert saved.leave_rate_confirmed_at == datetime(2026, 10, 25, 9, 0)
    assert AuditLog.query.filter_by(company_id=company.id, action='leave_rate_confirmation_change').count() == 0


def test_settings_form_without_leave_fields_keeps_confirmation(app, setup):
    company, user, _ = setup
    _confirm(company)
    client = app.test_client()
    _login(client, user)
    client.post('/settings/company', data={'name': company.name})
    db.session.expire_all()
    assert db.session.get(Company, company.id).leave_rate_confirmed_at is not None
