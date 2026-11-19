"""Owner decision Q1=A (docs/policy_decisions_2026-11-15.md): a final
settlement whose pending deductions exceed its earnings records a negative
net final payment — nothing is finalized until the user explicitly confirms
the recovery, and the confirmation is audited. The settlement detail page
shows a standing warning for negative settlements."""

import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

from payroll_engine import db
from payroll_engine.models import (
    AuditLog,
    Company,
    Employee,
    EmployeeDeduction,
    FinalSettlement,
    TenantQuery,
    User,
)

START = date(2024, 7, 31)
END = date(2026, 7, 31)


@pytest.fixture
def app():
    from payroll_engine import create_app

    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        from helpers import seed_synthetic_payroll_rule

        seed_synthetic_payroll_rule()
        for model in [Employee, EmployeeDeduction, FinalSettlement, AuditLog]:
            TenantQuery.register_model(model)
        yield app
        db.drop_all()


@pytest.fixture
def setup(app):
    company = Company(name='Synthetic Negative Co')
    # leave rule confirmed so the leave block does not mask the negative-net block
    company.leave_rate_confirmed_at = datetime(2026, 10, 25, 9, 0)
    db.session.add(company)
    db.session.flush()
    user = User(phone='911000778', company_id=company.id, role='owner')
    user.set_password('Test1234!')
    db.session.add(user)
    emp = Employee(
        employee_id='SYN-NEG-1',
        name='Synthetic Negative Worker',
        basic_salary=Decimal('10000'),
        allowances=Decimal('2000'),
        company_id=company.id,
        start_date=START,
    )
    db.session.add(emp)
    db.session.flush()
    # A salary advance of 30,000: pending deductions far exceed settlement earnings
    ded = EmployeeDeduction(
        employee_id=emp.id,
        company_id=company.id,
        deduction_type='advance',
        label='Salary advance',
        amount=Decimal('30000'),
        remaining_balance=Decimal('30000'),
        written_consent_recorded=True,
        written_consent_date=START,
        written_consent_reference='Synthetic signed consent TEST-NEG',
        written_consent_recorded_by=user.id,
        start_date=START,
        is_active=True,
    )
    db.session.add(ded)
    db.session.commit()
    return company, user, emp


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def _finalize_data(**extra):
    data = {
        'termination_reason': 'resignation',
        'password': 'Test1234!',
        'end_date': END.isoformat(),
        'unused_leave_days': '10',
    }
    data.update(extra)
    return data


def _confirmed_negative_data(setup):
    company, _user, emp = setup
    from payroll_engine.services.settlement_service import calculate_settlement

    calc = calculate_settlement(
        emp,
        'resignation',
        END,
        company.id,
        db.session,
        unused_leave_days=Decimal('10'),
    )
    return _finalize_data(
        confirm_negative_net='on',
        confirmed_negative_net=str(calc['net_final_payment'].quantize(Decimal('0.01'))),
    )


def test_preview_shows_negative_warning_and_confirm_checkbox(app, setup):
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
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'data-testid="negative-net-preview-warning"' in html
    assert 'data-testid="negative-net-confirm"' in html
    assert 'confirm_negative_net' in html
    db.session.expire_all()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0


def test_finalize_negative_without_confirm_is_blocked(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    resp = client.post(f'/employees/{emp.id}/terminate', data=_finalize_data())
    assert resp.status_code == 409
    html = resp.get_data(as_text=True)
    assert 'data-testid="settlement-finalize-blocked"' in html
    assert 'NEGATIVE final amount' in html
    assert 'data-testid="negative-net-confirm"' in html
    db.session.expire_all()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0
    assert db.session.get(Employee, emp.id).is_deleted is False
    assert EmployeeDeduction.query.filter_by(employee_id=emp.id, company_id=company.id, is_active=True).count() == 1


def test_finalize_negative_with_confirm_creates_settlement_and_audit(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    resp = client.post(f'/employees/{emp.id}/terminate', data=_confirmed_negative_data(setup))
    assert resp.status_code == 302
    db.session.expire_all()
    settlement = FinalSettlement.query.filter_by(company_id=company.id).one()
    assert settlement.net_final_payment < 0
    assert db.session.get(Employee, emp.id).is_deleted is True
    log = AuditLog.query.filter_by(company_id=company.id, action='employee_terminated').one()
    assert log.details['negative_net_confirmed'] is True
    assert log.details['net_final_payment'] == str(settlement.net_final_payment)


def test_positive_settlement_needs_no_confirm(app, setup):
    company, user, emp = setup
    # clear the advance so the settlement is comfortably positive
    db.session.query(EmployeeDeduction).filter_by(employee_id=emp.id).update({'is_active': False})
    db.session.commit()
    client = app.test_client()
    _login(client, user)
    resp = client.post(f'/employees/{emp.id}/terminate', data=_finalize_data())
    assert resp.status_code == 302
    db.session.expire_all()
    settlement = FinalSettlement.query.filter_by(company_id=company.id).one()
    assert settlement.net_final_payment > 0
    log = AuditLog.query.filter_by(company_id=company.id, action='employee_terminated').one()
    assert log.details['negative_net_confirmed'] is False


def test_direct_service_rejects_negative_without_confirm(app, setup):
    from payroll_engine.services import settlement_service

    company, user, emp = setup
    with pytest.raises(settlement_service.NegativeSettlementConfirmationError):
        settlement_service.create_settlement_record(
            emp,
            'resignation',
            END,
            company.id,
            user.id,
            db.session,
            unused_leave_days=10,
        )
    db.session.rollback()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0
    assert db.session.get(Employee, emp.id).is_deleted is False


def test_direct_service_rejects_wrong_confirmation_amount(app, setup):
    from payroll_engine.services import settlement_service

    company, user, emp = setup
    with pytest.raises(settlement_service.NegativeSettlementConfirmationError):
        settlement_service.create_settlement_record(
            emp,
            'resignation',
            END,
            company.id,
            user.id,
            db.session,
            unused_leave_days=10,
            confirm_negative_net=True,
            confirmed_negative_net=Decimal('-0.01'),
        )
    db.session.rollback()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0
    assert db.session.get(Employee, emp.id).is_deleted is False


def test_direct_service_accepts_exact_confirmed_negative(app, setup):
    from payroll_engine.services import settlement_service

    company, user, emp = setup
    calc = settlement_service.calculate_settlement(
        emp,
        'resignation',
        END,
        company.id,
        db.session,
        unused_leave_days=Decimal('10'),
    )
    settlement = settlement_service.create_settlement_record(
        emp,
        'resignation',
        END,
        company.id,
        user.id,
        db.session,
        unused_leave_days=Decimal('10'),
        confirm_negative_net=True,
        confirmed_negative_net=calc['net_final_payment'],
    )
    db.session.commit()

    assert settlement.net_final_payment < 0
    assert settlement.calculation_details['negative_net_confirmed'] is True
    assert settlement.calculation_details['negative_net_confirmed_amount'] == str(settlement.net_final_payment)


def test_route_rejects_tampered_confirmation_amount(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    resp = client.post(
        f'/employees/{emp.id}/terminate',
        data=_finalize_data(
            confirm_negative_net='on',
            confirmed_negative_net='-0.01',
        ),
    )

    assert resp.status_code == 409
    db.session.expire_all()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0
    assert db.session.get(Employee, emp.id).is_deleted is False


def test_changed_between_precheck_and_save_is_blocked(app, setup, monkeypatch):
    from payroll_engine.services import settlement_service

    company, user, emp = setup
    original = settlement_service.calculate_settlement
    calls = {'count': 0}

    def changed_calc(*args, **kwargs):
        calls['count'] += 1
        result = original(*args, **kwargs)
        if calls['count'] == 1:
            result = dict(result)
            result['net_final_payment'] = Decimal('125.00')
        elif calls['count'] == 2:
            result = dict(result)
            result['net_final_payment'] = Decimal('-275.00')
        return result

    monkeypatch.setattr(settlement_service, 'calculate_settlement', changed_calc)

    client = app.test_client()
    _login(client, user)
    resp = client.post(f'/employees/{emp.id}/terminate', data=_finalize_data())

    assert resp.status_code == 409
    db.session.expire_all()
    assert FinalSettlement.query.filter_by(company_id=company.id).count() == 0
    assert db.session.get(Employee, emp.id).is_deleted is False
    assert EmployeeDeduction.query.filter_by(employee_id=emp.id, company_id=company.id, is_active=True).count() == 1


def test_settlement_detail_shows_negative_warning(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    client.post(f'/employees/{emp.id}/terminate', data=_confirmed_negative_data(setup))
    db.session.expire_all()
    settlement = FinalSettlement.query.filter_by(company_id=company.id).one()
    resp = client.get(f'/settlements/{settlement.id}')
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'data-testid="negative-settlement-warning"' in html
    assert 'Negative final payment' in html
    assert 'data-testid="net-final-payment-summary"' in html
    assert f'Amount owed by the employee: ETB {abs(settlement.net_final_payment):.2f}' in html
    summary = html.split('data-testid="net-final-payment-summary"', 1)[1].split('<!-- Legal Reference -->', 1)[0]
    summary_tag = html.split('data-testid="net-final-payment-summary"', 1)[0].rsplit('<div', 1)[1]
    assert 'alert-danger' in summary_tag
    assert 'alert-success' not in summary_tag
    assert 'text-success' not in summary
    assert f'Amount payable to {emp.name}' not in summary


def test_settlement_detail_no_warning_when_positive(app, setup):
    company, user, emp = setup
    db.session.query(EmployeeDeduction).filter_by(employee_id=emp.id).update({'is_active': False})
    db.session.commit()
    client = app.test_client()
    _login(client, user)
    client.post(f'/employees/{emp.id}/terminate', data=_finalize_data())
    db.session.expire_all()
    settlement = FinalSettlement.query.filter_by(company_id=company.id).one()
    resp = client.get(f'/settlements/{settlement.id}')
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'data-testid="negative-settlement-warning"' not in html
    assert 'data-testid="net-final-payment-summary"' in html
    assert f'Amount payable to {emp.name}' in html
    assert f'ETB {settlement.net_final_payment:.2f}' in html
    summary = html.split('data-testid="net-final-payment-summary"', 1)[1].split('<!-- Legal Reference -->', 1)[0]
    summary_tag = html.split('data-testid="net-final-payment-summary"', 1)[0].rsplit('<div', 1)[1]
    assert 'alert-success' in summary_tag
    assert 'text-success' in summary


def test_settlement_detail_zero_keeps_payable_display(app, setup):
    company, user, emp = setup
    db.session.query(EmployeeDeduction).filter_by(employee_id=emp.id).update({'is_active': False})
    db.session.commit()
    client = app.test_client()
    _login(client, user)
    client.post(f'/employees/{emp.id}/terminate', data=_finalize_data())
    db.session.expire_all()
    settlement = FinalSettlement.query.filter_by(company_id=company.id).one()
    settlement.net_final_payment = Decimal('0.00')
    db.session.commit()

    resp = client.get(f'/settlements/{settlement.id}')
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'data-testid="negative-settlement-warning"' not in html
    assert 'data-testid="net-final-payment-summary"' in html
    assert f'Amount payable to {emp.name}' in html
    assert 'ETB 0.00' in html
    summary = html.split('data-testid="net-final-payment-summary"', 1)[1].split('<!-- Legal Reference -->', 1)[0]
    summary_tag = html.split('data-testid="net-final-payment-summary"', 1)[0].rsplit('<div', 1)[1]
    assert 'alert-success' in summary_tag
    assert 'text-success' in summary
