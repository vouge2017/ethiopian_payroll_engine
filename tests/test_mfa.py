"""Tests for MFA / TOTP functionality."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

import pyotp

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


def _create_user(ctx):
    """Create a test user and return (user, password)."""
    from payroll_engine.models import Company
    company = Company(name='TestCo')
    db.session.add(company)
    db.session.flush()
    user = User(phone='0911111111', role='owner', company_id=company.id)
    password = 'TestPass1!'
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, password


def _login(client, phone='0911111111', password='TestPass1!'):
    """Log in a test user."""
    client.post('/auth/login', data={
        'login_id': phone,
        'password': password,
    })


def test_mfa_setup_page_loads(client, ctx):
    """MFA setup page loads and shows QR code."""
    user, pw = _create_user(ctx)
    _login(client)
    resp = client.get('/auth/mfa/setup')
    assert resp.status_code == 200
    assert b'Two-Factor' in resp.data
    assert b'qrserver.com' in resp.data


def test_mfa_enable_with_valid_code(client, ctx):
    """Valid TOTP code enables MFA."""
    user, pw = _create_user(ctx)
    _login(client)

    # Generate secret
    client.get('/auth/mfa/setup')
    user = db.session.get(User, user.id)
    secret = user.totp_secret
    assert secret is not None

    # Generate valid code
    totp = pyotp.TOTP(secret)
    code = totp.now()

    resp = client.post('/auth/mfa/setup', data={'code': code}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'enabled' in resp.data.lower()

    user = db.session.get(User, user.id)
    assert user.mfa_enabled is True


def test_mfa_enable_with_invalid_code(client, ctx):
    """Invalid TOTP code does not enable MFA."""
    user, pw = _create_user(ctx)
    _login(client)
    client.get('/auth/mfa/setup')

    resp = client.post('/auth/mfa/setup', data={'code': '000000'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'invalid code' in resp.data.lower() or b'invalid' in resp.data.lower() or b'try again' in resp.data.lower()

    user = db.session.get(User, user.id)
    assert user.mfa_enabled is False


def test_mfa_verify_page_loads(client, ctx):
    """MFA verify page loads."""
    user, pw = _create_user(ctx)
    _login(client)
    resp = client.get('/auth/mfa/verify')
    assert resp.status_code == 200
    assert b'Verify' in resp.data or b'verification' in resp.data.lower()


def test_mfa_verify_sets_session_flag(client, ctx):
    """Successful MFA verification sets session flag."""
    user, pw = _create_user(ctx)
    _login(client)

    # Enable MFA
    client.get('/auth/mfa/setup')
    user = db.session.get(User, user.id)
    totp = pyotp.TOTP(user.totp_secret)
    client.post('/auth/mfa/setup', data={'code': totp.now()})

    # Verify MFA
    user = db.session.get(User, user.id)
    totp = pyotp.TOTP(user.totp_secret)
    resp = client.post('/auth/mfa/verify', data={'code': totp.now()}, follow_redirects=True)
    assert resp.status_code == 200

    # Check session has mfa_verified
    with client.session_transaction() as sess:
        assert sess.get('mfa_verified') is True


def test_mfa_disable(client, ctx):
    """MFA can be disabled with valid TOTP code."""
    user, pw = _create_user(ctx)
    _login(client)

    # Enable MFA
    client.get('/auth/mfa/setup')
    user = db.session.get(User, user.id)
    totp = pyotp.TOTP(user.totp_secret)
    client.post('/auth/mfa/setup', data={'code': totp.now()})

    # Disable MFA
    user = db.session.get(User, user.id)
    totp = pyotp.TOTP(user.totp_secret)
    resp = client.post('/auth/mfa/disable', data={'code': totp.now()}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'disabled' in resp.data.lower()

    user = db.session.get(User, user.id)
    assert user.mfa_enabled is False
    assert user.totp_secret is None


def test_mfa_already_enabled_shows_info(client, ctx):
    """If MFA is already enabled, setup page redirects with info."""
    user, pw = _create_user(ctx)
    _login(client)

    # Enable MFA
    client.get('/auth/mfa/setup')
    user = db.session.get(User, user.id)
    totp = pyotp.TOTP(user.totp_secret)
    client.post('/auth/mfa/setup', data={'code': totp.now()})

    # Try to access setup again
    resp = client.get('/auth/mfa/setup', follow_redirects=True)
    assert resp.status_code == 200
    assert b'already enabled' in resp.data.lower()


def test_user_model_totp_methods(ctx):
    """Test User model TOTP methods directly."""
    from payroll_engine.models import Company
    company = Company(name='TestCo2')
    db.session.add(company)
    db.session.flush()
    user = User(phone='0922222222', role='owner', company_id=company.id)
    user.set_password('dummy')
    db.session.add(user)
    db.session.commit()

    # Generate secret
    secret = user.generate_totp_secret()
    assert len(secret) >= 16  # Base32 secret (pyotp generates 32-char by default)
    assert user.totp_secret == secret

    # Get URI
    uri = user.get_totp_uri()
    assert 'otpauth://totp/' in uri
    assert 'EthioPayroll' in uri

    # Enable MFA first (verify_totp bypasses when mfa_enabled=False)
    user.enable_mfa()
    assert user.mfa_enabled is True

    # Verify valid code
    totp = pyotp.TOTP(secret)
    assert user.verify_totp(totp.now()) is True

    # Verify invalid code
    assert user.verify_totp('000000') is False

    user.disable_mfa()
    assert user.mfa_enabled is False
    assert user.totp_secret is None
    # When MFA disabled, verify always passes
    assert user.verify_totp('anything') is True
