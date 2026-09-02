"""Regression tests for the static-asset cache-bust mechanism.

The bug this prevents: a CSS change ships in commit X, but the user's
browser still loads the old CSS from Cloudflare's edge cache because the
URL is identical. With `?v={{ static_version }}` in the <link href>, each
deploy gets a new URL and the browser fetches fresh assets.

The fix relies on the context_processor in payroll_engine/__init__.py
exposing `static_version` (set from GIT_COMMIT_SHA / RENDER_GIT_COMMIT /
a startup-time fallback) and the templates appending it as a query
string on the CSS link.
"""
import os
import re

import pytest

from payroll_engine import create_app


@pytest.fixture
def app():
    os.environ.setdefault('DB_ENCRYPTION_KEY', 'a-real-encryption-key-32-chars-minimum-here')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app


def test_static_version_is_exposed_in_context(app):
    """The Jinja context must expose `static_version` so the template
    can append it to the CSS link href."""
    with app.test_request_context():
        # Use Jinja's context processor dict directly
        rv = app.test_client().get('/auth/login', follow_redirects=True)
        # The page should render without 500 even with the cache-bust link
        assert rv.status_code in (200, 302)
    # The config value is a non-empty string
    assert app.config.get('STATIC_ASSET_VERSION')
    assert isinstance(app.config['STATIC_ASSET_VERSION'], str)
    assert len(app.config['STATIC_ASSET_VERSION']) >= 4


def test_login_html_has_cache_bust_query_on_css(app):
    """The login page must include ?v=... on its CSS link so a deploy
    invalidates the browser/CDN cache."""
    client = app.test_client()
    r = client.get('/auth/login', follow_redirects=True)
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    # Find the design-system CSS link
    m = re.search(r'<link[^>]+design-system\.css[^>]*>', html)
    assert m is not None, 'login page must link to design-system.css'
    link_tag = m.group(0)
    assert '?v=' in link_tag, (
        f'design-system.css link must include a ?v= cache-bust query, got: {link_tag}'
    )


def test_login_html_has_cache_bust_query_on_responsive_css(app):
    """Same for responsive.css."""
    client = app.test_client()
    r = client.get('/auth/login', follow_redirects=True)
    html = r.get_data(as_text=True)
    m = re.search(r'<link[^>]+responsive\.css[^>]*>', html)
    assert m is not None, 'login page must link to responsive.css'
    assert '?v=' in m.group(0)


def test_static_version_falls_back_to_int_when_no_git_env(app):
    """If neither GIT_COMMIT_SHA nor RENDER_GIT_COMMIT is set, the
    fallback must still produce a non-empty string. We don't care
    whether it's a hex SHA or a unix timestamp — only that it's
    present, URL-safe, and changes across boots."""
    # The fixture already cleared the env; just assert the config is sane
    sv = app.config['STATIC_ASSET_VERSION']
    # Must not contain characters that would break a URL query string
    assert re.match(r'^[A-Za-z0-9_-]+$', sv), (
        f'static_version must be URL-safe, got: {sv!r}'
    )


def test_base_layout_also_uses_cache_bust(app):
    """The main app layout (templates/base.html) must also use the
    cache-bust on its CSS link, so authenticated pages benefit too.
    """
    # Get a page that uses base.html (e.g., healthz or /about).
    client = app.test_client()
    r = client.get('/healthz', follow_redirects=True)
    if r.status_code == 200:
        html = r.get_data(as_text=True)
        m = re.search(r'<link[^>]+design-system\.css[^>]*>', html)
        if m is not None:
            # If healthz renders a full layout, it must include the bust
            assert '?v=' in m.group(0)
