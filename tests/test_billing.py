"""
Billing spine v0 tests.

Covers:
- effective_billing_status state machine (trial / active / grace / suspension)
- employee tier caps (manual create + bulk import headroom math)
- request gate behavior: read-only on past_due, hard block on suspended,
  API JSON 402s
- reconciliation flow: tenant submits reference -> operator confirms ->
  company active through paid month, plan upgrade applied
"""

import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.billing import (
    BILLING_GRACE_DAYS,
    effective_billing_status,
    get_plan,
)
from payroll_engine.models import BillingPayment, Company, User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def _company(**kw):
    defaults = {'name': 'Test Co'}
    defaults.update(kw)
    c = Company(**defaults)
    db.session.add(c)
    db.session.commit()
    return c


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


def test_trialing_without_end_is_grandfathered(app):
    assert effective_billing_status(_company()) == 'trialing'


def test_trialing_within_window(app):
    c = _company(trial_ends_at=datetime.utcnow() + timedelta(days=5))
    assert effective_billing_status(c) == 'trialing'


def test_expired_trial_becomes_past_due(app):
    c = _company(trial_ends_at=datetime.utcnow() - timedelta(days=2))
    assert effective_billing_status(c) == 'past_due'


def test_active_with_future_paid_until(app):
    c = _company(billing_status='active', paid_until=date.today() + timedelta(days=10))
    assert effective_billing_status(c) == 'active'


def test_active_recently_lapsed_is_past_due(app):
    c = _company(billing_status='active', paid_until=date.today() - timedelta(days=1))
    assert effective_billing_status(c) == 'past_due'


def test_active_lapsed_beyond_grace_suspends():
    """Derived suspension works even without touching stored status."""
    c = Company(
        name='Lapsed',
        billing_status='active',
        paid_until=date.today() - timedelta(days=BILLING_GRACE_DAYS + 1),
    )
    assert effective_billing_status(c) == 'suspended'


def test_operator_suspend_overrides_everything():
    c = Company(
        name='Killed',
        billing_status='suspended',
        paid_until=date.today() + timedelta(days=30),
    )
    assert effective_billing_status(c) == 'suspended'


# ---------------------------------------------------------------------------
# Tier caps
# ---------------------------------------------------------------------------


def test_plan_lookup_falls_back_to_free(app):
    assert get_plan(Company(name='x', plan_code='nonsense'))['max_employees'] == 5


def test_employee_slot_cap(app):
    from payroll_engine.billing import check_employee_slot
    from payroll_engine.models import Employee

    c = _company(plan_code='free')  # max 5
    for i in range(5):
        db.session.add(
            Employee(company_id=c.id, name=f'E{i}', employee_id=f'EMP{i:03d}', basic_salary=100)
        )
    db.session.commit()
    ok, err = check_employee_slot(c)
    assert not ok and '5 employees' in err

    # Soft-deleted employees do not consume slots
    emp = Employee.query.filter_by(company_id=c.id).first()
    emp.is_deleted = True
    db.session.commit()
    ok, err = check_employee_slot(c)
    assert ok and err is None


# ---------------------------------------------------------------------------
# Request gate + reconciliation flow
# ---------------------------------------------------------------------------


def _login(client, user):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True


def _owner(company_id=None, platform=False):
    u = User(email=f'{"plat" if platform else "own"}{datetime.utcnow().timestamp()}@t.et',
             password_hash='x', role='owner',
             company_id=company_id, is_platform_admin=platform)
    db.session.add(u)
    db.session.commit()
    return u


def test_gate_blocks_writes_when_past_due(app):
    client = app.test_client()
    c = _company(billing_status='active', paid_until=date.today() - timedelta(days=1))
    u = _owner(c.id)
    _login(client, u)

    resp = client.post('/employees/add', data={'name': 'X'})
    assert resp.status_code == 302
    assert '/billing' in resp.headers['Location']


def test_gate_redirects_suspended_to_blocked(app):
    client = app.test_client()
    c = _company(billing_status='suspended')
    u = _owner(c.id)
    _login(client, u)

    resp = client.get('/employees')
    assert resp.status_code == 302
    assert '/billing/blocked' in resp.headers['Location']

    # Billing pages themselves stay reachable
    assert client.get('/billing').status_code == 200
    assert client.get('/billing/blocked').status_code == 200


def test_api_gets_json_402_when_past_due(app):
    client = app.test_client()
    c = _company(billing_status='active', paid_until=date.today() - timedelta(days=1))
    u = _owner(c.id)
    _login(client, u)

    resp = client.post('/api/v1/employees/bulk', json={'employees': [{'name': 'A'}]})
    assert resp.status_code == 402
    assert resp.is_json


def test_tenant_can_submit_payment_reference(app):
    client = app.test_client()
    with app.app_context():
        c = _company(plan_code='free')
        owner = _owner(c.id)
        uid, cid = owner.id, c.id
    def login(client, uid):
        with client.session_transaction() as sess:
            sess['_user_id'] = str(uid); sess['_fresh'] = True
    login(client, uid)
    resp = client.post('/billing/submit-payment',
        data={'period_month': '2026-09', 'plan_code': 'standard', 'reference': 'FT123'},
        follow_redirects=True)
    assert resp.status_code == 200
    with app.app_context():
        p = BillingPayment.query.one()
        assert p.status == 'pending' and p.plan_code == 'standard'
        assert float(p.amount_etb) == 500.0


def test_operator_confirm_activates_company(app):
    """Confirmation half, isolated: seed pending payment, operator confirms."""
    with app.app_context():
        c = _company(plan_code='free')
        opco = _company(name='Platform HQ')
        operator = User(email='op@t.et', password_hash='x', role='owner',
                        company_id=opco.id, is_platform_admin=True)
        db.session.add(operator)
        db.session.flush()
        pay = BillingPayment(company_id=c.id, plan_code='standard',
                             amount_etb=500, period_month='2026-09',
                             reference='FT-SEED', status='pending')
        db.session.add(pay)
        db.session.commit()
        pid, oid, cid = pay.id, operator.id, c.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(oid); sess['_fresh'] = True
    resp = client.post(f'/platform/payments/{pid}/confirm', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        db.session.expire_all()
        company = db.session.get(Company, cid)
        assert company.billing_status == 'active'
        assert company.plan_code == 'standard'
        assert str(company.paid_until) == '2026-09-30'
        assert BillingPayment.query.get(pid).status == 'confirmed'


