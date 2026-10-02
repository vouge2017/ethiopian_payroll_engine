"""Restored registration rules must not strand existing phone identities."""

import pytest

from payroll_engine import create_app, db, limiter
from payroll_engine.models import Company, LoginAttempt, SupportTicket, SupportTicketMessage, User


@pytest.fixture
def app():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    previous = limiter.enabled
    limiter.enabled = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    limiter.enabled = previous


def add_user(phone, company_id=None):
    user = User(phone=phone, company_id=company_id, role='owner')
    user.set_password('SyntheticPass123!')
    db.session.add(user)
    db.session.commit()
    return user.id


@pytest.mark.parametrize('stored', ['0911234567', '911234567'])
@pytest.mark.parametrize('entered', ['0911234567', '911234567', '+251 911 234 567'])
def test_legacy_phone_login_preserves_identity(app, stored, entered):
    with app.app_context():
        company = Company(name='Synthetic identity')
        db.session.add(company)
        db.session.commit()
        user_id = add_user(stored, company.id)
    client = app.test_client()
    response = client.post('/auth/login', data={'login_id': entered, 'password': 'SyntheticPass123!'})
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session['_user_id'] == str(user_id)
    with app.app_context():
        assert User.query.filter_by(id=user_id).one().phone == stored


def test_phone_aliases_share_durable_lockout_without_tenant(app):
    with app.app_context():
        add_user('911234567')
    client = app.test_client()
    for entered in ['0911234567', '+251911234567', '911234567', '0911234567', '+251911234567']:
        response = client.post('/auth/login', data={'login_id': entered, 'password': 'Wrong'}, follow_redirects=True)
        assert response.status_code == 200
    with app.app_context():
        assert LoginAttempt.query.filter_by(identifier='911234567', success=False).count() == 5
    response = client.post(
        '/auth/login', data={'login_id': '911234567', 'password': 'SyntheticPass123!'}, follow_redirects=True
    )
    assert b'temporarily locked' in response.data
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_ambiguous_legacy_and_new_accounts_cannot_choose_identity(app):
    with app.app_context():
        add_user('0911234567')
        add_user('911234567')
    client = app.test_client()
    response = client.post(
        '/auth/login', data={'login_id': '911234567', 'password': 'SyntheticPass123!'}, follow_redirects=True
    )
    assert b'Invalid credentials' in response.data
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_support_models_require_company_filter(app):
    with app.app_context():
        for model in (SupportTicket, SupportTicketMessage):
            with pytest.raises(RuntimeError, match='TENANT ISOLATION VIOLATION'):
                model.query.all()


def test_tenant_cannot_open_another_company_support_ticket(app):
    with app.app_context():
        a, b = Company(name='Synthetic A'), Company(name='Synthetic B')
        db.session.add_all([a, b])
        db.session.commit()
        user_id = add_user('911234567', a.id)
        ticket = SupportTicket(ticket_code='SYNTHETIC-B', company_id=b.id, subject='Private')
        db.session.add(ticket)
        db.session.commit()
        ticket_id, company_id = ticket.id, a.id
    client = app.test_client()
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True
        session['company_id'] = company_id
    response = client.get(f'/support/tickets/{ticket_id}')
    assert response.status_code == 404


def test_new_registration_cannot_shadow_a_legacy_phone(app):
    with app.app_context():
        original = add_user('0911234567')
    response = app.test_client().post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SyntheticPass123!',
            'password2': 'SyntheticPass123!',
        },
    )
    assert response.status_code == 400
    with app.app_context():
        assert User.query.count() == 1
        assert User.query.filter_by(id=original).one().phone == '0911234567'


@pytest.mark.parametrize('entered', ['0911234567', '911234567'])
def test_password_recovery_keeps_legacy_identity(app, monkeypatch, entered):
    tokens = []
    original_generate = User.generate_reset_token

    def capture(user):
        token = original_generate(user)
        tokens.append(token)
        return token

    monkeypatch.setattr(User, 'generate_reset_token', capture)
    with app.app_context():
        original = add_user('0911234567')
    client = app.test_client()
    assert client.post('/auth/forgot-password', data={'login_id': entered}).status_code == 302
    assert len(tokens) == 1
    response = client.post('/auth/reset-password/verify', data={'token': tokens[0]})
    assert response.status_code == 302 and '/auth/reset-password/new' in response.headers['Location']
    response = client.post(
        '/auth/reset-password/new',
        data={
            'password': 'NewSyntheticPass123!',
            'password2': 'NewSyntheticPass123!',
        },
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session['_user_id'] == str(original)
    with app.app_context():
        user = User.query.filter_by(id=original).one()
        assert user.phone == '0911234567' and user.check_password('NewSyntheticPass123!')
