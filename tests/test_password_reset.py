"""Tests for password reset flow."""

import os
import sys

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


def test_forgot_password_page_loads(client):
    """GET /auth/forgot-password shows the form."""
    resp = client.get('/auth/forgot-password')
    assert resp.status_code == 200
    assert b'Forgot Password' in resp.data


def test_forgot_password_with_phone(client):
    """POST with valid phone generates reset token."""
    user = User(phone='911111111', role='owner')
    user.set_password('TestPass1!')
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        pass  # Ensure clean session

    resp = client.post(
        '/auth/forgot-password',
        data={'login_id': '911111111'},
        follow_redirects=False,
    )
    # Should redirect to verify page
    assert resp.status_code == 302
    assert '/auth/reset-password/verify' in resp.headers.get('Location', '')

    # Verify token was stored
    refreshed = db.session.get(User, user.id)
    assert refreshed.reset_token_hash is not None


def test_forgot_password_with_email(client):
    """POST with valid email generates reset token."""
    user = User(email='test@example.com', phone='922222222', role='owner')
    user.set_password('TestPass1!')
    db.session.add(user)
    db.session.commit()

    resp = client.post(
        '/auth/forgot-password',
        data={'login_id': 'test@example.com'},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert '/auth/reset-password/verify' in resp.headers.get('Location', '')


def test_forgot_password_nonexistent_user(client):
    """POST with unknown phone still shows same generic message (no user enumeration)."""
    resp = client.post(
        '/auth/forgot-password',
        data={'login_id': '999999999'},
        follow_redirects=False,
    )
    # Should redirect to verify page (same response for security)
    assert resp.status_code == 302
    assert '/auth/reset-password/verify' in resp.headers.get('Location', '')


def test_reset_password_flow_integration(client):
    """Full integration test for password reset using the actual flow."""
    # Create user WITH a company to bypass progressive profiling redirect
    from payroll_engine.models import Company
    company = Company(name='Test Reset Company')
    db.session.add(company)
    db.session.flush()

    user = User(phone='933333333', role='owner', company_id=company.id)
    user.set_password('OldPass1!')
    db.session.add(user)
    db.session.commit()

    # Step 1: Request reset
    resp = client.post(
        '/auth/forgot-password',
        data={'login_id': '933333333'},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    # Get the raw token
    token = user.generate_reset_token()
    db.session.commit()

    # Step 2: Verify token
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '933333333',
            'verified': True,
            'code_attempts': 0,
        }

    resp = client.post(
        '/auth/reset-password/verify',
        data={'token': token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert '/auth/reset-password/new' in resp.headers.get('Location', '')

    # Step 3: Set new password
    resp = client.post(
        '/auth/reset-password/new',
        data={
            'password': 'NewPass1!',
            'password2': 'NewPass1!',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # After successful reset, user is redirected to main.index (dashboard)
    # since they already have a company
    assert b'reset successfully' in resp.data.lower() or b'log in' in resp.data.lower() or b'welcome' in resp.data.lower()

    # Verify password was changed
    refreshed = db.session.get(User, user.id)
    assert refreshed.check_password('NewPass1!')
    assert not refreshed.check_password('OldPass1!')


def test_reset_password_weak_password_rejected(client):
    """Password must meet strength requirements including symbol."""
    user = User(phone='944444444', role='owner')
    user.set_password('OldPass1!')
    db.session.add(user)
    db.session.commit()

    # Get token
    token = user.generate_reset_token()
    db.session.commit()

    # Set up session for verified user
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '944444444',
            'verified': True,
            'code_attempts': 0,
        }

    # Try weak password (missing symbol)
    resp = client.post(
        '/auth/reset-password/new',
        data={
            'password': 'WeakPass1',
            'password2': 'WeakPass1',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Should reject for missing symbol
    assert b'symbol' in resp.data.lower()

    # Password should NOT be changed
    refreshed = db.session.get(User, user.id)
    assert refreshed.check_password('OldPass1!')


def test_reset_password_mismatch_rejected(client):
    """POST with mismatched passwords is rejected."""
    user = User(phone='955555555', role='owner')
    user.set_password('OldPass1!')
    db.session.add(user)
    db.session.commit()

    # Set up session for verified user
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '955555555',
            'verified': True,
            'code_attempts': 0,
        }

    # Try mismatched passwords
    resp = client.post(
        '/auth/reset-password/new',
        data={
            'password': 'NewPass1!',
            'password2': 'DifferentPass!',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b'do not match' in resp.data.lower()

    refreshed = db.session.get(User, user.id)
    assert refreshed.check_password('OldPass1!')


def test_login_page_has_forgot_password_link(client):
    """Login page includes a forgot password link."""
    resp = client.get('/auth/login')
    assert resp.status_code == 200
    assert b'forgot' in resp.data.lower()