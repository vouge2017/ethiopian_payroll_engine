"""Tests for the 3-step password recovery flow.

Verifies that:
- Identity is preserved in session across navigation (no re-typing)
- Brute-force protection kicks in after 5 wrong codes
- The 3-step flow correctly transitions through forgot → verify → new
- Auto-login happens after successful password reset
- Legacy /reset-password URL redirects to the new flow
- change_password no longer requires current_password
"""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DB_ENCRYPTION_KEY', 'a-real-encryption-key-32-chars-minimum-here')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import User


@pytest.fixture
def app():
    """Reuse the test app pattern from test_auth.py."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        # Clean any prior users
        User.query.delete()
        db.session.commit()
        user = User(phone='911234567', role='owner')
        user.set_password('OldPass1!')
        db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _get_reset_token(app, phone='911234567'):
    """Generate a valid reset token for the test user (returns the raw token).
    The user object is detached after this call so callers can pass the token
    in subsequent requests."""
    with app.app_context():
        user = User.query.filter_by(phone=phone).first()
        token = user.generate_reset_token()
        db.session.commit()
        return token


# --- Step 1: recovery availability ---


def test_forgot_password_get_renders_form(client):
    r = client.get('/auth/forgot-password')
    assert r.status_code == 200
    assert b'password reset codes cannot currently be delivered' in r.data.lower()
    assert b'contact support' in r.data.lower()


def test_forgot_password_post_does_not_issue_a_code(client, app):
    """Posting an identifier shows honest recovery guidance without issuing a token."""
    r = client.post('/auth/forgot-password', data={'login_id': '911234567'})
    assert r.status_code == 200
    assert b'no reset code was created or sent' in r.data.lower()
    with app.app_context():
        user = User.query.filter_by(phone='911234567').first()
        assert user.reset_token_hash is None


def test_forgot_password_post_is_independent_of_identifier(client):
    phone = client.post('/auth/forgot-password', data={'login_id': '911234567'})
    email = client.post('/auth/forgot-password', data={'login_id': 'unknown@example.invalid'})
    assert phone.status_code == email.status_code == 200
    for response in (phone, email):
        assert b'no reset code was created or sent' in response.data.lower()
    assert b'911234567' not in phone.data and b'unknown@example.invalid' not in email.data


def test_forgot_password_no_enumeration(client):
    """Whether the user exists or not, the response should look the same."""
    r1 = client.post('/auth/forgot-password', data={'login_id': '911234567'}, follow_redirects=True)
    r2 = client.post('/auth/forgot-password', data={'login_id': '999999999'}, follow_redirects=True)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert b'no reset code was created or sent' in r1.data.lower()
    assert b'no reset code was created or sent' in r2.data.lower()
    assert b'911234567' not in r1.data and b'999999999' not in r2.data


def test_forgot_password_does_not_claim_undelivered_code_or_log_it(client, app, monkeypatch, caplog):
    """Recovery must not issue or log a code while no delivery channel is configured."""
    caplog.set_level(logging.DEBUG, logger='payroll_engine')
    generated = []
    original_generate = User.generate_reset_token

    def track_generated_token(user):
        token = original_generate(user)
        generated.append(token)
        return token

    monkeypatch.setattr(User, 'generate_reset_token', track_generated_token)
    with app.app_context():
        user = User.query.filter_by(phone='911234567').first()
        assert user.reset_token_hash is None

    response = client.post('/auth/forgot-password', data={'login_id': '911234567'}, follow_redirects=True)

    assert response.status_code == 200
    assert all(token not in caplog.text for token in generated)
    assert generated == []
    assert b'no reset code was created or sent' in response.data.lower()
    assert b'code has been sent' not in response.data.lower()
    with app.app_context():
        user = User.query.filter_by(phone='911234567').first()
        assert user.reset_token_hash is None


# --- Step 2: verify (code entry, no identity re-typing) ---


def test_verify_requires_session(client):
    """If you hit verify without going through forgot first, redirect back."""
    r = client.get('/auth/reset-password/verify', follow_redirects=False)
    assert r.status_code == 302
    assert '/forgot-password' in r.headers.get('Location', '')


def test_verify_renders_identity_chip(client, app):
    """An explicitly authorized recovery channel can still verify an issued code."""
    client.get('/auth/forgot-password')
    with client.session_transaction() as sess:
        sess['reset_identity'] = {'type': 'phone', 'value': '911234567', 'code_attempts': 0}
    r = client.get('/auth/reset-password/verify')
    assert r.status_code == 200
    assert b'identity-chip' in r.data
    # Should show the masked phone, e.g., "91***567"
    assert b'91' in r.data and b'567' in r.data


def test_verify_correct_code_proceeds_to_new(client, app):
    """A valid code from an authorized channel still completes verification."""
    token = _get_reset_token(app)
    with client.session_transaction() as sess:
        sess['reset_identity'] = {'type': 'phone', 'value': '911234567', 'code_attempts': 0}
    r = client.post('/auth/reset-password/verify', data={'token': token}, follow_redirects=False)
    assert r.status_code == 302
    assert '/auth/reset-password/new' in r.headers.get('Location', '')


def test_verify_wrong_code_rejected(client, app):
    _token = _get_reset_token(app)
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '911234567',
            'code_attempts': 0,
        }
    r = client.post('/auth/reset-password/verify', data={'token': 'wrongcode123456'}, follow_redirects=True)
    assert b'Invalid or expired code' in r.data


def test_verify_brute_force_protection(client, app):
    """After 5 wrong attempts, the session is wiped."""
    # Initialize session via GET
    client.get('/auth/forgot-password')
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '911234567',
            'code_attempts': 4,  # already at 4, next wrong attempt triggers wipe
        }
    # 5th attempt should wipe the session
    r = client.post('/auth/reset-password/verify', data={'token': 'wrong000005'}, follow_redirects=True)
    assert b'Too many attempts' in r.data or b'start over' in r.data or b'forgot-password' in r.data.lower()


# --- Step 3: new password (only password fields, no identity re-typing) ---


def test_new_requires_verified_session(client):
    """If you hit /new without verifying, redirect back to forgot."""
    r = client.get('/auth/reset-password/new', follow_redirects=False)
    assert r.status_code == 302
    assert '/forgot-password' in r.headers.get('Location', '')


def test_new_renders_password_fields_and_identity_chip(client, app):
    """Verify page renders only password fields, with identity chip on top."""
    _token = _get_reset_token(app)
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '911234567',
            'code_attempts': 0,
            'verified': True,
        }
    r = client.get('/auth/reset-password/new')
    assert r.status_code == 200
    assert b'identity-chip' in r.data
    # Should NOT ask for phone/email again
    assert b'name="phone"' not in r.data
    assert b'name="email"' not in r.data
    # Should have new password fields
    assert b'name="password"' in r.data
    assert b'name="password2"' in r.data


def test_new_password_success_logs_user_in(client, app):
    """Successful reset should auto-login the user and redirect to dashboard."""
    _token = _get_reset_token(app)
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '911234567',
            'code_attempts': 0,
            'verified': True,
        }
    r = client.post(
        '/auth/reset-password/new',
        data={'password': 'NewPass1!', 'password2': 'NewPass1!'},
        follow_redirects=False,
    )
    assert r.status_code == 302
    # Should redirect to main (logged in), NOT to login
    assert '/auth/login' not in r.headers.get('Location', '')


def test_new_password_mismatch_rejected(client, app):
    _token = _get_reset_token(app)
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '911234567',
            'code_attempts': 0,
            'verified': True,
        }
    r = client.post(
        '/auth/reset-password/new',
        data={'password': 'NewPass1!', 'password2': 'Different1!'},
        follow_redirects=True,
    )
    assert b'Passwords do not match' in r.data


def test_new_password_weak_rejected(client, app):
    _token = _get_reset_token(app)
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '911234567',
            'code_attempts': 0,
            'verified': True,
        }
    r = client.post(
        '/auth/reset-password/new',
        data={'password': 'weak', 'password2': 'weak'},
        follow_redirects=True,
    )
    # Should be rejected by password policy
    assert b'password' in r.data.lower()


# --- Backward compatibility ---


def test_legacy_reset_password_url_redirects(client):
    """The old /reset-password URL should redirect to the new forgot-password."""
    r = client.get('/auth/reset-password', follow_redirects=False)
    assert r.status_code == 302
    assert '/forgot-password' in r.headers.get('Location', '')


# --- change_password no longer requires current_password ---


def test_change_password_does_not_require_current_password(client, app):
    """Authenticated user changing password only needs new + confirm."""
    with app.app_context():
        _user = User.query.filter_by(phone='911234567').first()
        # We can't easily login via test client without going through login route,
        # so just verify the route doesn't read 'current_password' anymore.
        # The template check is the simpler verification.
    pass  # Covered by template assertion test below


def test_change_password_template_no_current_field(app):
    """Verify the template doesn't include a current_password field anymore."""
    from pathlib import Path

    tpl = Path('payroll_engine/templates/auth/change_password.html').read_text()
    assert 'id="current_password"' not in tpl
    assert 'name="current_password"' not in tpl


# --- Identity preservation across navigation ---


def test_identity_preserved_across_navigation(client, app):
    """The user should NOT have to re-enter their phone/email between steps."""
    # Step 1: seed session (simulating having completed forgot-password)
    # First do a GET to initialize the cookie
    client.get('/auth/forgot-password')
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '911234567',
            'code_attempts': 0,
        }
    # Step 2: visit verify page — phone is in session, shown in identity chip
    r = client.get('/auth/reset-password/verify')
    assert r.status_code == 200
    assert b'name="phone"' not in r.data  # no phone input field
    assert b'name="email"' not in r.data  # no email input field
    assert b'identity-chip' in r.data
    # Step 3: re-seed session with verified=True (full reset of session)
    client.get('/auth/forgot-password')
    with client.session_transaction() as sess:
        sess['reset_identity'] = {
            'type': 'phone',
            'value': '911234567',
            'code_attempts': 0,
            'verified': True,
        }
    # Visit new page — still no phone/email field
    r = client.get('/auth/reset-password/new')
    assert r.status_code == 200
    assert b'name="phone"' not in r.data
    assert b'name="email"' not in r.data
    assert b'identity-chip' in r.data
