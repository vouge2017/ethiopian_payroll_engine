"""Tests for the progressive profiling onboarding flow.

After register (Step 1: phone + password only), the user is auto-logged-in
with `must_complete_profile=True` and redirected to /auth/setup-profile
(Step 2) to collect first/middle/last name + company name.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DB_ENCRYPTION_KEY', 'a-real-encryption-key-32-chars-minimum-here')
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')

import pytest

from payroll_engine import create_app, db
from payroll_engine.models import Company, User


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['RATELIMIT_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# --- Step 1: register collects only phone + password ---

def test_register_collects_only_phone_and_password(client):
    """Step 1 form should not include first_name, middle_name, last_name, or company_name fields."""
    r = client.get('/auth/register')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    # Required fields
    assert 'name="phone"' in html
    assert 'name="password"' in html
    assert 'name="password2"' in html
    # Optional email
    assert 'name="email"' in html
    # NOT collected at register
    assert 'name="first_name"' not in html
    assert 'name="middle_name"' not in html
    assert 'name="last_name"' not in html
    assert 'name="company_name"' not in html


def test_register_creates_user_with_must_complete_profile(client, app):
    """After register, user must_complete_profile=True, company_id=None."""
    r = client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    # Should redirect to /auth/setup-profile, not /auth/login
    assert '/auth/setup-profile' in r.headers.get('Location', '')

    with app.app_context():
        user = User.query.filter_by(phone='911234567').first()
        assert user is not None
        assert user.must_complete_profile is True
        assert user.company_id is None
        assert user.first_name is None
        assert user.last_name is None


def test_register_auto_logs_in_user(client, app):
    """After register, user is auto-logged-in (no separate login step)."""
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
        follow_redirects=False,
    )
    # User should be logged in — accessing a protected page should NOT redirect to login
    r = client.get('/auth/setup-profile', follow_redirects=False)
    assert r.status_code == 200


# --- Step 2: setup-profile collects name + company ---

def test_setup_profile_redirects_logged_out_users(client):
    """Anonymous users should be redirected to login."""
    r = client.get('/auth/setup-profile', follow_redirects=False)
    assert r.status_code == 302
    assert '/auth/login' in r.headers.get('Location', '')


def test_setup_profile_renders_form_for_logged_in_user(client, app):
    """Logged-in user with must_complete_profile=True sees the form."""
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    r = client.get('/auth/setup-profile')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'name="first_name"' in html
    assert 'name="last_name"' in html
    assert 'name="company_name"' in html
    # Identity chip
    assert 'identity-chip' in html


def test_setup_profile_completes_registration(client, app):
    """Submitting name + company creates the company and clears the flag."""
    # Step 1
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    # Step 2
    r = client.post(
        '/auth/setup-profile',
        data={
            'first_name': 'Abebe',
            'middle_name': 'Bekele',
            'last_name': 'Kebede',
            'company_name': 'Acme Ethiopia',
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert r.headers.get('Location', '').endswith('/')

    with app.app_context():
        user = User.query.filter_by(phone='911234567').first()
        assert user is not None
        assert user.must_complete_profile is False
        assert user.first_name == 'Abebe'
        assert user.middle_name == 'Bekele'
        assert user.last_name == 'Kebede'
        assert user.company_id is not None
        company = Company.query.get(user.company_id)
        assert company is not None
        assert company.name == 'Acme Ethiopia'


def test_setup_profile_requires_first_and_last_name(client, app):
    """Missing first/last name should be rejected."""
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    r = client.post(
        '/auth/setup-profile',
        data={
            'first_name': '',
            'last_name': '',
            'company_name': 'Acme',
        },
        follow_redirects=False,
    )
    assert r.status_code == 400
    body = r.get_data(as_text=True)
    assert 'First name and last name are required' in body


def test_setup_profile_requires_company_name(client, app):
    """Missing company name should be rejected."""
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    r = client.post(
        '/auth/setup-profile',
        data={
            'first_name': 'Abebe',
            'last_name': 'Kebede',
            'company_name': '',
        },
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_setup_profile_rejects_duplicate_company_name(client, app):
    """If company name exists, the user must choose a different name."""
    # Pre-create the company
    with app.app_context():
        Company.query.delete()
        existing = Company(name='Existing Co')
        db.session.add(existing)
        db.session.commit()
    # Register a new user
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    r = client.post(
        '/auth/setup-profile',
        data={
            'first_name': 'Abebe',
            'last_name': 'Kebede',
            'company_name': 'Existing Co',
        },
        follow_redirects=False,
    )
    assert r.status_code == 400
    body = r.get_data(as_text=True)
    assert 'already exists' in body


# --- Skip option ---

def test_setup_profile_skip_clears_flag(client, app):
    """User can skip profile setup; must_complete_profile becomes False."""
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    r = client.get('/auth/setup-profile/skip', follow_redirects=False)
    assert r.status_code == 302

    with app.app_context():
        user = User.query.filter_by(phone='911234567').first()
        assert user is not None
        assert user.must_complete_profile is False


# --- before_request hook: forces profile setup until complete ---

def test_must_complete_profile_redirects_to_setup(client, app):
    """Logged-in user with must_complete_profile=True is forced to /auth/setup-profile."""
    # Register
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    # Try to access main.index — should be redirected to /auth/setup-profile or /setup-company
    r = client.get('/', follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers.get('Location', '')
    assert '/auth/setup-profile' in loc or '/setup-company' in loc


def test_must_complete_profile_allows_setup_profile_access(client, app):
    """Logged-in user with must_complete_profile=True can access /auth/setup-profile."""
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    r = client.get('/auth/setup-profile', follow_redirects=False)
    assert r.status_code == 200  # No redirect — allowed


def test_completed_profile_does_not_redirect(client, app):
    """After profile is complete, user can access main routes normally."""
    client.post(
        '/auth/register',
        data={
            'phone': '911234567',
            'password': 'SecurePass123!',
            'password2': 'SecurePass123!',
        },
    )
    # Complete the profile
    client.post(
        '/auth/setup-profile',
        data={
            'first_name': 'Abebe',
            'last_name': 'Kebede',
            'company_name': 'Acme',
        },
    )
    # Now main.index should NOT redirect to /auth/setup-profile
    # (It may redirect elsewhere for auth or business reasons, but not to setup-profile)
    r = client.get('/', follow_redirects=False)
    # If 200, user is on dashboard. If 302, redirect target should not be setup-profile.
    if r.status_code == 302:
        assert '/auth/setup-profile' not in r.headers.get('Location', '')
