"""Wave 1 security regression tests.

These tests deliberately attack the previous failure modes — they are not
happy-path smoke checks. Each assertion maps to a real abuse path.
"""

import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine import create_app, db
from payroll_engine.models import Employee, OvertimeEntry, TenantQuery, User
from payroll_engine.security import safe_redirect_target


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['ENABLE_DEMO_MODE'] = True
    # Disable rate limiting noise in tests
    app.config['RATELIMIT_ENABLED'] = False
    with app.app_context():
        db.create_all()
        TenantQuery.register_model(Employee)
        TenantQuery.register_model(OvertimeEntry)
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _register(client, phone='911234567', password='SecurePass123!', company='SecureCo'):
    return client.post(
        '/auth/register',
        data={
            'phone': phone,
            'email': f'{phone}@test.com',
            'password': password,
            'password2': password,
            'company_name': company,
        },
        follow_redirects=True,
    )


def _login(client, phone='911234567', password='SecurePass123!', next_url=None, follow=False):
    from urllib.parse import quote

    url = '/auth/login'
    if next_url is not None:
        url = f'/auth/login?next={quote(next_url, safe="")}'
    return client.post(
        url,
        data={'login_id': phone, 'password': password},
        follow_redirects=follow,
    )


def _register_and_login(client, phone='911234567', password='SecurePass123!', company='SecureCo'):
    _register(client, phone=phone, password=password, company=company)
    return _login(client, phone=phone, password=password, follow=True)


# ---------------------------------------------------------------------------
# #1 Open redirect
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'evil_next',
    [
        'https://evil.example/phish',
        'http://evil.example/phish',
        '//evil.example/phish',
        '/\\evil.example',
        '///evil.example',
        'https://evil.example/?next=/employees',
    ],
)
def test_login_blocks_external_next_redirect(client, app, evil_next):
    """Unauthenticated login with attacker-controlled ?next= must not leave host."""
    _register(client)
    # Must be logged OUT so safe_redirect_target is actually exercised
    client.get('/auth/logout', follow_redirects=True)

    resp = _login(client, next_url=evil_next, follow=False)
    assert resp.status_code == 302
    location = resp.headers.get('Location', '')
    assert 'evil.example' not in location
    assert not location.startswith('//')
    # Lands on a same-app path (default index or relative)
    assert location.startswith('/') or 'localhost' in location or '127.0.0.1' in location


def test_login_allows_local_next_redirect(client, app):
    """Login may redirect to same-host relative paths."""
    _register(client)
    client.get('/auth/logout', follow_redirects=True)

    resp = _login(client, next_url='/employees', follow=False)
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/employees')


def test_safe_redirect_target_unit(app):
    """Direct unit coverage for redirect sanitizer edge cases."""
    with app.test_request_context('/auth/login', base_url='http://localhost/'):
        assert safe_redirect_target(None).endswith('/')
        assert safe_redirect_target('/employees') == '/employees'
        assert safe_redirect_target('/employees?tab=1') == '/employees?tab=1'
        assert safe_redirect_target('https://evil.example/x') != 'https://evil.example/x'
        assert 'evil' not in safe_redirect_target('//evil.example/x')
        assert 'evil' not in safe_redirect_target('/\\evil.example')
        # Absolute same-host (Referer-style) collapses to path
        assert safe_redirect_target('http://localhost/reports') == '/reports'


# ---------------------------------------------------------------------------
# #2 Predictable temp passwords
# ---------------------------------------------------------------------------


def test_invite_uses_unpredictable_password_shown_once(client, app):
    """Invite must not use phone-derived passwords or flash plaintext."""
    _register_and_login(client)

    resp = client.post(
        '/settings/team/invite',
        data={
            'phone': '944444444',
            'name': 'New Hire',
            'role': 'accountant',
        },
        follow_redirects=False,
    )

    assert resp.status_code == 200
    body = resp.data.decode('utf-8', errors='replace')

    # Credentials page renders
    assert 'One-time temporary password' in body
    # Legacy predictable pattern must never appear
    assert '444444Temp1!' not in body
    assert 'Temp1!' not in body

    # Extract the shown password from <code>...</code>
    codes = re.findall(r'<code[^>]*>([^<]+)</code>', body)
    assert codes, 'Expected temporary password in response body'
    temp_password = codes[-1].strip()
    assert len(temp_password) >= 16
    # token_urlsafe alphabet — not a phone suffix
    assert not temp_password.endswith('Temp1!')
    assert '944444444'[-6:] not in temp_password

    with app.app_context():
        invited = User.query.filter_by(phone='944444444').first()
        assert invited is not None
        assert invited.must_change_password is True
        assert invited.check_password(temp_password)
        # Password is hashed only — no recoverable column
        assert invited.password_hash != temp_password

    # Flash messages must not contain the password
    # Re-login as owner and re-check a second invite isn't needed; verify
    # HTML does not put password into a flash alert with the old wording.
    assert 'Temporary password:' not in body


def test_invited_user_must_change_password_before_app_use(client, app):
    """Temp password login is forced into change-password before any app route."""
    _register_and_login(client)
    resp = client.post(
        '/settings/team/invite',
        data={
            'phone': '955555555',
            'name': 'Forced Change',
            'role': 'accountant',
        },
    )
    body = resp.data.decode('utf-8', errors='replace')
    codes = re.findall(r'<code[^>]*>([^<]+)</code>', body)
    temp_password = codes[-1].strip()

    client.get('/auth/logout', follow_redirects=True)

    login_resp = _login(client, phone='955555555', password=temp_password, follow=False)
    assert login_resp.status_code == 302
    assert '/auth/change-password' in login_resp.headers.get('Location', '')

    # Cannot reach protected app routes until password is changed
    dash = client.get('/', follow_redirects=False)
    assert dash.status_code in (302, 401)
    if dash.status_code == 302:
        assert '/auth/change-password' in dash.headers.get('Location', '')

    # Complete forced change
    change = client.post(
        '/auth/change-password',
        data={
            'current_password': temp_password,
            'new_password': 'brandNewPass9!',
            'new_password2': 'brandNewPass9!',
        },
        follow_redirects=False,
    )
    assert change.status_code == 302
    assert '/auth/change-password' not in change.headers.get('Location', '')

    with app.app_context():
        invited = User.query.filter_by(phone='955555555').first()
        assert invited.must_change_password is False
        assert invited.check_password('brandNewPass9!')
        assert not invited.check_password(temp_password)

    # Now the app is usable
    dash2 = client.get('/', follow_redirects=True)
    assert dash2.status_code == 200


# ---------------------------------------------------------------------------
# #3 Exception leakage
# ---------------------------------------------------------------------------


def test_payroll_upload_error_does_not_leak_exception_text(client, app):
    """Payroll upload failures must not expose raw exception details to users."""
    _register_and_login(client)

    data = {
        'file': (io.BytesIO(b'not,a,valid,payroll\n'), 'bad.csv'),
    }
    resp = client.post(
        '/payroll',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    assert resp.status_code == 200
    body = resp.data
    assert b'Reference:' in body
    # Previous implementation flashed: Error processing payroll: {e}
    assert b'Missing required columns' not in body
    assert b'ValueError' not in body
    assert b'Traceback' not in body
    assert b'Error processing payroll:' not in body


# ---------------------------------------------------------------------------
# #4 Open /demo route
# ---------------------------------------------------------------------------


def test_demo_route_disabled_when_flag_off(client, app):
    """Public demo auto-login must be unavailable when disabled."""
    app.config['ENABLE_DEMO_MODE'] = False
    resp = client.get('/demo')
    assert resp.status_code == 404


def test_demo_route_enabled_when_flag_on(client, app):
    """Demo route works when explicitly enabled (dev/demo only)."""
    app.config['ENABLE_DEMO_MODE'] = True
    resp = client.get('/demo', follow_redirects=True)
    assert resp.status_code == 200


def test_login_page_hides_demo_when_disabled(client, app):
    """Login CTA for demo must not appear when demo mode is off."""
    app.config['ENABLE_DEMO_MODE'] = False
    resp = client.get('/auth/login')
    assert resp.status_code == 200
    assert b'Try with sample data' not in resp.data
    assert b'/demo' not in resp.data


def test_login_page_shows_demo_when_enabled(client, app):
    app.config['ENABLE_DEMO_MODE'] = True
    resp = client.get('/auth/login')
    assert resp.status_code == 200
    assert b'Try with sample data' in resp.data


def test_production_config_forces_demo_off():
    """Production must hard-disable demo auto-login (class-level lock)."""
    from config import ProductionConfig

    assert ProductionConfig.ENABLE_DEMO_MODE is False
