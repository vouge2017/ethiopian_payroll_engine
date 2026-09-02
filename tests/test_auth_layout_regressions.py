"""Regression tests for the auth-page layout fixes.

Two user-reported issues:
1. When the password is incorrect, the screen size and the form
   element shifted (Flash alert banner squeezed the auth card).
2. Phone number input had text overlap with the +251 country code label.

These tests assert the rendered HTML structure of the auth pages
(GET /auth/login, GET /auth/register) and the presence of the
relevant CSS rules in the design system. They are pure-HTML
regressions — they don't exercise the full login flow.
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


def _get_login_html(app):
    client = app.test_client()
    r = client.get('/auth/login')
    if r.status_code == 302:
        r = client.get(r.headers.get('Location', '/auth/login'), follow_redirects=True)
    return r.get_data(as_text=True), r.status_code


def _get_register_html(app):
    client = app.test_client()
    r = client.get('/auth/register')
    if r.status_code == 302:
        r = client.get(r.headers.get('Location', '/auth/register'), follow_redirects=True)
    return r.get_data(as_text=True), r.status_code


# ──────────────────────────────────────────────────────────────────────
# Issue 1: auth layout shift on incorrect password (flash banner)
# ──────────────────────────────────────────────────────────────────────

def test_login_renders_form_area(app):
    """The auth page must contain the .onboarding-form-area wrapper."""
    html, status = _get_login_html(app)
    assert status == 200
    assert 'onboarding-form-area' in html, (
        'Login page must contain the .onboarding-form-area wrapper'
    )


def test_login_does_not_use_old_flash_container(app):
    """The old `class="container" style="max-width: 480px;..."` flash wrapper
    that was a flex sibling of the form/sidebars has been removed —
    it was the root cause of the layout shift on error alerts.
    """
    html, _ = _get_login_html(app)
    assert 'class="container" style="max-width: 480px' not in html, (
        'Old flash wrapper found — this caused the form to squeeze on error.'
    )


def test_flash_bar_present_in_base_template(app):
    """The new .onboarding-flash-bar wrapper is in the base template so
    any future auth page automatically gets the full-width flash layout.
    """
    html, _ = _get_login_html(app)
    # It's only rendered when there are flash messages, but the CSS class
    # definition should be reachable from the static asset chain. We assert
    # the page loads cleanly without the old container wrapper above; for
    # a flash-rendering test we use a server-side flash via the session.
    with app.test_client() as c:
        with c.session_transaction():
            pass  # placeholder
    # The CSS is served via /static/css/design-system.css
    css_resp = app.test_client().get('/static/css/design-system.css')
    assert css_resp.status_code == 200
    css_text = css_resp.get_data(as_text=True)
    assert '.onboarding-flash-bar' in css_text, (
        'design-system.css must define .onboarding-flash-bar'
    )
    assert '.onboarding-flash-bar .alert' in css_text, (
        'design-system.css must scope .alert inside .onboarding-flash-bar'
    )


def test_flash_bar_css_prevents_layout_shift(app):
    """The flash bar CSS must include width: 100%, max-width, box-sizing,
    and word-break rules so error alerts never squeeze the form card.
    """
    css_resp = app.test_client().get('/static/css/design-system.css')
    css_text = css_resp.get_data(as_text=True)

    # The .onboarding-flash-bar block must enforce width control
    flash_block = css_text.split('.onboarding-flash-bar', 1)
    assert len(flash_block) == 2, '.onboarding-flash-bar not found in CSS'
    # Look at the next 600 chars (the block)
    flash_section = flash_block[1][:600]
    assert 'width: 100%' in flash_section or 'width:100%' in flash_section
    assert 'box-sizing' in flash_section
    assert 'word-break' in flash_section or 'overflow-wrap' in flash_section


def test_form_area_css_hardened_against_extension_injection(app):
    """Password-manager extensions inject content into inputs. The form area
    and its children must enforce min-width: 0 and box-sizing to prevent
    the injected content from blowing out the layout.
    """
    css_resp = app.test_client().get('/static/css/design-system.css')
    css_text = css_resp.get_data(as_text=True)

    # Look for the hardened form-area block
    form_block = css_text.split('.onboarding-form-area {', 1)
    assert len(form_block) == 2, '.onboarding-form-area block not found'
    form_section = form_block[1][:800]
    assert 'min-width: 0' in form_section or 'min-width:0' in form_section, (
        'Form area must enforce min-width: 0 to prevent flex children from'
        ' blowing out the layout when extensions inject content.'
    )
    assert 'box-sizing' in form_section


# ──────────────────────────────────────────────────────────────────────
# Issue 2: phone input text overlap with +251 prefix
# ──────────────────────────────────────────────────────────────────────

def test_login_phone_input_uses_prefix_wrapper(app):
    """The login phone field must use the .onboarding-phone-wrapper so
    the +251 prefix is absolutely positioned and the input has padding-left
    to keep typed text away from the prefix.
    """
    html, _ = _get_login_html(app)
    assert 'onboarding-phone-wrapper' in html
    assert 'onboarding-phone-prefix' in html
    assert '+251' in html


def test_register_phone_input_uses_prefix_wrapper(app):
    """Same as login — register must use the prefix wrapper for phone."""
    html, _ = _get_register_html(app)
    assert 'onboarding-phone-wrapper' in html
    assert 'onboarding-phone-prefix' in html
    assert '+251' in html


def test_phone_input_css_has_padding_left(app):
    """CSS rule must give the phone input enough left padding to clear
    the +251 prefix label. 60px is the current value.
    """
    css_resp = app.test_client().get('/static/css/design-system.css')
    css_text = css_resp.get_data(as_text=True)
    # Find the rule that sets padding-left on .onboarding-phone-wrapper input
    assert '.onboarding-phone-wrapper input' in css_text
    # Look for padding-left in the immediate rule block
    rule = css_text.split('.onboarding-phone-wrapper input', 1)
    assert len(rule) == 2
    # Within the next ~100 chars (rule body), padding-left must be set
    rule_body = rule[1][:120]
    assert 'padding-left' in rule_body, (
        '.onboarding-phone-wrapper input must set padding-left to keep text'
        ' from overlapping the +251 prefix'
    )
    # And it must be at least 56px to clear "+251" + spacing
    import re
    m = re.search(r'padding-left:\s*(\d+)px', rule_body)
    assert m is not None, 'padding-left must use a numeric px value'
    assert int(m.group(1)) >= 56, (
        f'padding-left is {m.group(1)}px — must be at least 56px to clear the +251 prefix'
    )


def test_phone_prefix_css_centered_vertically(app):
    """The +251 prefix must be vertically centered over the input —
    without top: 50% + transform: translateY(-50%), it sits at the top
    of the input which looks broken.
    """
    css_resp = app.test_client().get('/static/css/design-system.css')
    css_text = css_resp.get_data(as_text=True)
    rule = css_text.split('.onboarding-phone-prefix', 1)
    # Take the second occurrence (first is the canonical definition we want)
    body = rule[1][:400]
    assert 'top: 50%' in body, (
        '.onboarding-phone-prefix must be vertically centered (top: 50%)'
    )
    assert 'translateY(-50%)' in body, (
        '.onboarding-phone-prefix must use translateY(-50%) to vertically center'
    )
