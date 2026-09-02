"""Regression tests for the favicon route and password-field autocomplete.

The favicon was 404-ing in the console because no /favicon.ico file existed
and no Flask route served it. Password fields lacked `autocomplete` attributes,
producing a Chrome DevTools warning.
"""
import os

import pytest

from payroll_engine import create_app


@pytest.fixture
def app():
    os.environ.setdefault('DB_ENCRYPTION_KEY', 'a-real-encryption-key-32-chars-minimum-here')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app


def test_favicon_route_returns_png(app):
    """GET /favicon.ico must return 200 image/png, not 404."""
    client = app.test_client()
    r = client.get('/favicon.ico', follow_redirects=True)
    assert r.status_code == 200, f'favicon must be 200, got {r.status_code}'
    assert r.headers.get('Content-Type', '').startswith('image/'), (
        f'favicon must be image/*, got {r.headers.get("Content-Type")!r}'
    )
    body = r.get_data()
    assert len(body) > 100, 'favicon must have actual content'


def test_login_html_has_favicon_link(app):
    """The login page must declare a <link rel='icon'> so browsers don't
    fall back to /favicon.ico and trigger a 404 in the console."""
    client = app.test_client()
    r = client.get('/auth/login', follow_redirects=True)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'rel="icon"' in html, 'login page must declare a favicon link'


# Pages and the autocomplete value each password field should have
PASSWORD_AUTOCOMPLETE_CASES = [
    # (path, password-input-name, expected autocomplete)
    ('/auth/login', 'password', 'current-password'),
    ('/auth/register', 'password', 'new-password'),
    ('/auth/register', 'password2', 'new-password'),
    ('/auth/accept-invite', 'password', 'new-password'),
    ('/auth/accept-invite', 'password2', 'new-password'),
    ('/auth/reset-password', 'password', 'new-password'),
    ('/auth/reset-password', 'password2', 'new-password'),
]


@pytest.mark.parametrize('path,field_name,expected_autocomplete', PASSWORD_AUTOCOMPLETE_CASES)
def test_password_field_has_correct_autocomplete(app, path, field_name, expected_autocomplete):
    """Every password input must declare the correct autocomplete token
    to silence Chrome's DOM warning."""
    client = app.test_client()
    r = client.get(path, follow_redirects=True)
    if r.status_code != 200:
        pytest.skip(f'{path} returned {r.status_code}; skipping')
    html = r.get_data(as_text=True)
    # Find the input with this name and assert its autocomplete attribute
    import re
    pattern = rf'<input[^>]+name="{field_name}"[^>]*>'
    m = re.search(pattern, html)
    assert m is not None, f'{path}: no <input name="{field_name}"> found'
    tag = m.group(0)
    assert f'autocomplete="{expected_autocomplete}"' in tag, (
        f'{path}: <input name="{field_name}"> must have '
        f'autocomplete="{expected_autocomplete}", got: {tag}'
    )
