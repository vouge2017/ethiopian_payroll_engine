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
    resp = client.post(f'/employees/{emp.id}/terminate', data=_finalize_data(confirm_negative_net='on'))
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


def test_settlement_detail_shows_negative_warning(app, setup):
    company, user, emp = setup
    client = app.test_client()
    _login(client, user)
    client.post(f'/employees/{emp.id}/terminate', data=_finalize_data(confirm_negative_net='on'))
    db.session.expire_all()
    settlement = FinalSettlement.query.filter_by(company_id=company.id).one()
    resp = client.get(f'/settlements/{settlement.id}')
    html = resp.get_data(as_text=True)
    assert 'data-testid="negative-settlement-warning"' in html
    assert 'Negative final payment' in html


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
    assert 'data-testid="negative-settlement-warning"' not in resp.get_data(as_text=True)
