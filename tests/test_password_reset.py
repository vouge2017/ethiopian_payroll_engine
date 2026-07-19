"""Tests for password reset flow."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import User


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


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_forgot_password_page_loads(client):
    """GET /auth/forgot-password shows the form."""
    resp = client.get('/auth/forgot-password')
    assert resp.status_code == 200
    assert b'Forgot Password' in resp.data


def test_forgot_password_with_phone(client, ctx):
    """POST with valid phone generates reset token."""
    user = User(phone='0911111111', role='owner')
    user.set_password('TestPass1!')
    db.session.add(user)
    db.session.commit()

    resp = client.post('/auth/forgot-password', data={
        'login_id': '0911111111',
    }, follow_redirects=True)
    assert resp.status_code == 200
    # Should show generic message (no token exposure)
    assert b'if an account' in resp.data.lower() or b'reset code' in resp.data.lower()

    # Verify token was stored
    refreshed = db.session.get(User, user.id)
    assert refreshed.reset_token_hash is not None
    assert refreshed.reset_token_expires is not None


def test_forgot_password_with_email(client, ctx):
    """POST with valid email generates reset token."""
    user = User(email='test@example.com', phone='0922222222', role='owner')
    user.set_password('TestPass1!')
    db.session.add(user)
    db.session.commit()

    resp = client.post('/auth/forgot-password', data={
        'login_id': 'test@example.com',
    }, follow_redirects=True)
    assert resp.status_code == 200

    refreshed = db.session.get(User, user.id)
    assert refreshed.reset_token_hash is not None


def test_forgot_password_nonexistent_user(client, ctx):
    """POST with unknown phone still shows generic message (no user enumeration)."""
    resp = client.post('/auth/forgot-password', data={
        'login_id': '0999999999',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'if an account' in resp.data.lower()


def test_reset_password_with_valid_token(client, ctx):
    """POST /auth/reset-password with valid token in form body resets password."""
    user = User(phone='0933333333', role='owner')
    user.set_password('OldPass1!')
    db.session.add(user)
    db.session.commit()

    token = user.generate_reset_token()
    db.session.commit()

    resp = client.post('/auth/reset-password', data={
        'token': token,
        'password': 'NewPass1!',
        'password2': 'NewPass1!',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'reset successfully' in resp.data.lower() or b'log in' in resp.data.lower()

    # Verify password was changed
    refreshed = db.session.get(User, user.id)
    assert refreshed.check_password('NewPass1!')
    assert not refreshed.check_password('OldPass1!')
    # Token should be cleared
    assert refreshed.reset_token_hash is None


def test_reset_password_with_invalid_token(client, ctx):
    """POST with invalid token shows error."""
    resp = client.post('/auth/reset-password', data={
        'token': 'invalidtoken123',
        'password': 'NewPass1!',
        'password2': 'NewPass1!',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'invalid' in resp.data.lower() or b'expired' in resp.data.lower()


def test_reset_password_weak_password_rejected(client, ctx):
    """POST with weak password is rejected."""
    user = User(phone='0944444444', role='owner')
    user.set_password('OldPass1!')
    db.session.add(user)
    db.session.commit()

    token = user.generate_reset_token()
    db.session.commit()

    resp = client.post('/auth/reset-password', data={
        'token': token,
        'password': 'Password1',
        'password2': 'Password1',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'too common' in resp.data.lower()

    # Password should NOT be changed
    refreshed = db.session.get(User, user.id)
    assert refreshed.check_password('OldPass1!')


def test_reset_password_mismatch_rejected(client, ctx):
    """POST with mismatched passwords is rejected."""
    user = User(phone='0955555555', role='owner')
    user.set_password('OldPass1!')
    db.session.add(user)
    db.session.commit()

    token = user.generate_reset_token()
    db.session.commit()

    resp = client.post('/auth/reset-password', data={
        'token': token,
        'password': 'NewPass1!',
        'password2': 'DifferentPass1!',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'do not match' in resp.data.lower()

    refreshed = db.session.get(User, user.id)
    assert refreshed.check_password('OldPass1!')


def test_login_page_has_forgot_password_link(client):
    """Login page includes a forgot password link."""
    resp = client.get('/auth/login')
    assert resp.status_code == 200
    assert b'forgot' in resp.data.lower()
