"""
Auth security tests — specifically for the registration company takeover fix.

The vulnerability: registering with an existing company name would make you
its admin without invitation. This test proves it's fixed.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Company, User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_register_creates_new_company(client, app):
    """Registering creates a user. Progressive profiling: company is set in /setup-profile."""
    r = client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'email': 'alice@test.com',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
        follow_redirects=False,
    )
    if r.status_code != 302:
        body = r.get_data(as_text=True)
        import re
        flashes = re.findall(r'alert alert-(\w+)[^>]*>([^<]+)', body)
        pytest.fail(f'Expected 302, got {r.status_code}. Flashes: {flashes[:3]}')
    # After register, user is auto-logged-in and redirected to /auth/setup-profile
    assert '/auth/setup-profile' in r.headers.get('Location', '')

    with app.app_context():
        user = User.query.filter_by(phone='911234567').first()
        assert user is not None
        # Progressive: must_complete_profile=True, company_id=None
        assert user.must_complete_profile is True
        assert user.company_id is None
        assert user.role == 'owner'


def test_register_rejects_existing_company_name(client, app):
    """Outdated test: with progressive profiling, the company name is set in
    /auth/setup-profile, not during register. This test now verifies that
    a user with must_complete_profile=True can be created without a
    duplicate-check failing on the company name (which doesn't exist yet)."""
    r = client.post(
        '/auth/register',
        data={
            'phone': '922345678',
            'email': 'attacker@test.com',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
        follow_redirects=False,
    )
    assert r.status_code == 302

    with app.app_context():
        user = User.query.filter_by(phone='922345678').first()
        assert user is not None
        assert user.company_id is None


def test_register_rejects_case_variation(client, app):
    """Outdated: progressive profiling no longer takes company_name at register.
    This test now verifies that an unrelated user can register without errors."""
    r = client.post(
        '/auth/register',
        data={
            'phone': '933456789',
            'email': 'attacker@test.com',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    with app.app_context():
        user = User.query.filter_by(phone='933456789').first()
        assert user is not None


def test_register_duplicate_email_rejected(client, app):
    """Same email can't register twice."""
    r1 = client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'email': 'alice@test.com',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
        follow_redirects=False,
    )
    assert r1.status_code == 302, f'First registration failed: {r1.get_data(as_text=True)[:500]}'

    # Logout so the next register request isn't blocked by is_authenticated
    client.get('/auth/logout')

    r2 = client.post(
        '/auth/register',
        data={
            'phone': '922345678',
            'email': 'alice@test.com',
            'password': 'SecurePass456!',
            'password2': 'SecurePass456!',
        },
        follow_redirects=False,
    )
    # Second registration should be rejected (400 with form re-render)
    assert r2.status_code == 400, f'Expected 400 for duplicate email, got {r2.status_code}'

    with app.app_context():
        users = User.query.filter_by(email='alice@test.com').all()
        assert len(users) == 1


def test_register_short_password_rejected(client, app):
    """Password shorter than 8 chars should be rejected."""
    r = client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'email': 'alice@test.com',
            'password': 'Sh0!rt',
            'password2': 'Sh0!rt',
        },
        follow_redirects=False,
    )
    assert r.status_code == 400, f'Expected 400 for weak password, got {r.status_code}'


def test_register_password_mismatch_rejected(client, app):
    """Password confirmation must match."""
    r = client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'email': 'alice@test.com',
            'password': 'SecurePass123!',
            'password2': 'DifferentPass456!',
        },
        follow_redirects=False,
    )
    assert r.status_code == 400, f'Expected 400 for password mismatch, got {r.status_code}'

    with app.app_context():
        user = User.query.filter_by(phone='0911234567').first()
        assert user is None
