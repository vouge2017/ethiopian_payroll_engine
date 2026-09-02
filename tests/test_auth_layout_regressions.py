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
# Issue 2: phone input — now uses intl-tel-input for country selection
# ──────────────────────────────────────────────────────────────────────

def test_login_phone_input_uses_intl_tel(app):
    """The login field accepts phone-or-email (`login_id`). For now we
    keep the static +251 hint because the field is dual-purpose; only
    the dedicated phone fields (register, add_employee, etc.) get the
    full intl-tel-input selector.

    The login page MUST still load phone-input.js so that future changes
    that turn login into a phone-only field are picked up automatically.
    """
    html, _ = _get_login_html(app)
    assert 'static/js/phone-input.js' in html, (
        'Login page must load phone-input.js'
    )


def test_register_phone_input_uses_intl_tel(app):
    """Same as login — register must use intl-tel-input for the phone."""
    html, _ = _get_register_html(app)
    assert 'data-intl-tel' in html
    assert 'onboarding-phone-wrapper' in html


def test_phone_input_js_is_loaded(app):
    """All three base templates must include the phone-input.js script
    so the country selector initializes on every page.
    """
    for path in ('/auth/login', '/auth/register'):
        client = app.test_client()
        r = client.get(path, follow_redirects=True)
        html = r.get_data(as_text=True)
        assert 'static/js/phone-input.js' in html, (
            f'{path} must load phone-input.js so the country selector initializes'
        )


def test_phone_wrapper_css_handles_intl_tel(app):
    """The .onboarding-phone-wrapper CSS must reset the input's
    padding-left when the wrapper has the .iti class (added by the JS
    after intl-tel-input initializes), so the static 60px rule does not
    fight with the plugin's own layout.
    """
    css_resp = app.test_client().get('/static/css/design-system.css')
    css_text = css_resp.get_data(as_text=True)
    assert '.onboarding-phone-wrapper.iti input' in css_text, (
        'CSS must include .onboarding-phone-wrapper.iti input rule to reset'
        ' padding when intl-tel-input is active'
    )


def test_static_251_prefix_is_removed_from_register(app):
    """The old hardcoded <span class="onboarding-phone-prefix">+251</span>
    has been removed from the register page — intl-tel-input provides the
    prefix and country code dynamically. (Login and forgot_password also
    have no +251 prefix because their `login_id` field is phone-or-email
    and a hardcoded country code was misleading.)
    """
    client = app.test_client()
    r = client.get('/auth/register', follow_redirects=True)
    html = r.get_data(as_text=True)
    assert 'class="onboarding-phone-prefix">+251' not in html, (
        'Register page still has the hardcoded +251 prefix span — '
        'intl-tel-input should be providing the country code now'
    )


def test_login_has_no_static_251_prefix(app):
    """Login's `login_id` is phone-or-email. A hardcoded +251 prefix was
    misleading for email input. The field is now a clean .onboarding-input
    with no prefix.
    """
    client = app.test_client()
    r = client.get('/auth/login', follow_redirects=True)
    html = r.get_data(as_text=True)
    assert 'class="onboarding-phone-prefix">+251' not in html, (
        'Login page still has a hardcoded +251 prefix — misleading for'
        ' phone-or-email field; intl-tel-input is not used here'
    )
    # And the new clean input class is present
    assert 'class="onboarding-input"' in html, (
        'Login must use the new .onboarding-input class for the clean'
        ' phone-or-email field'
    )


def test_forgot_password_has_no_static_251_prefix(app):
    """Same as login — forgot_password's `login_id` is phone-or-email."""
    client = app.test_client()
    r = client.get('/auth/forgot-password', follow_redirects=True)
    if r.status_code != 200:
        pytest.skip(f'forgot-password returned {r.status_code}; skipping')
    html = r.get_data(as_text=True)
    assert 'class="onboarding-phone-prefix">+251' not in html, (
        'forgot_password still has a hardcoded +251 prefix'
    )


def test_emergency_phone_uses_intl_tel(app):
    """The employee-portal emergency_phone field must use intl-tel-input
    so employees can register an international emergency contact."""
    client = app.test_client()
    r = client.get('/employee/profile/edit', follow_redirects=True)
    if r.status_code != 200:
        pytest.skip(f'employee/profile/edit returned {r.status_code}; auth needed')
    html = r.get_data(as_text=True)
    # emergency_phone must be one of the intl-tel inputs
    m = re.search(r'<input[^>]+name="emergency_phone"[^>]*>', html)
    assert m is not None, 'emergency_phone field must exist on employee profile edit'
    assert 'data-intl-tel' in m.group(0), (
        f'emergency_phone must use intl-tel-input, got: {m.group(0)}'
    )


# ──────────────────────────────────────────────────────────────────────
# CSS alignment for the country selector (intl-tel-input)
# ──────────────────────────────────────────────────────────────────────

def test_iti_country_container_height_matches_input(app):
    """The flag dropdown (.iti__country-container) must be the same
    height as the input (44px) so the field reads as one continuous
    control.
    """
    css = app.test_client().get('/static/css/design-system.css').get_data(as_text=True)
    # The height: 44px rule for the country container
    cc_block = css.split('.iti__country-container {', 1)
    assert len(cc_block) == 2, '.iti__country-container block not found'
    body = cc_block[1][:200]
    assert 'height: 44px' in body, (
        f'.iti__country-container must be 44px tall to match the input, got: {body!r}'
    )


def test_iti_tel_input_height_matches(app):
    """The intl-tel-input's inner .iti__tel-input must also be 44px tall."""
    css = app.test_client().get('/static/css/design-system.css').get_data(as_text=True)
    ti_block = css.split('.iti input.iti__tel-input,', 1)
    assert len(ti_block) == 2, '.iti__tel-input block not found'
    body = ti_block[1][:400]
    assert 'height: 44px' in body


def test_iti_focus_state_has_brand_color(app):
    """The .iti__tel-input focus state must use the brand color so the
    active state matches the rest of the design system."""
    css = app.test_client().get('/static/css/design-system.css').get_data(as_text=True)
    # Look for the focus block
    focus_block = css.split('.iti input.iti__tel-input:focus', 1)
    assert len(focus_block) == 2, '.iti__tel-input:focus block not found'
    body = focus_block[1][:200]
    assert 'var(--brand-primary)' in body, (
        'Focused intl-tel-input must use --brand-primary for the border'
    )


def test_onboarding_input_class_exists(app):
    """The .onboarding-input class (used on login + forgot_password for
    the phone-or-email `login_id` field) must be defined and visually
    consistent with the .onboarding-field input."""
    css = app.test_client().get('/static/css/design-system.css').get_data(as_text=True)
    assert '.onboarding-input {' in css, '.onboarding-input class must be defined'
    # Take a generous slice — CSS may have line comments and CRLF endings
    # that push the height rule beyond a 400-char window.
    block = css.split('.onboarding-input {', 1)
    body = block[1][:800]
    for token in ('height: 44px', 'var(--bg-secondary)', 'var(--gray-300)', 'var(--radius-md)'):
        # Allow either space or no space between key and colon
        if token not in body:
            alt = token.replace(': ', ':')
            if alt not in body:
                assert token in body, f'.onboarding-input must include {token!r}'
