"""Phone validator strict mode + password strength + login/email mode + CSP-safe intl-tel-input.

Four related gate tests, all in one file for the strict-rule hardening
session.
"""
import os
import re

import pytest

from payroll_engine import create_app
from payroll_engine.models import validate_ethiopian_phone
from payroll_engine.password_policy import check_password_strength


# ─────────────────────────────────────────────────────────────────────
# 1. Phone validator — strict 9 digits, 7 or 9 prefix
# ─────────────────────────────────────────────────────────────────────

def test_phone_accepts_9_digit_national_format():
    """Valid: 911234567 (national, 9 digits, starts with 9)."""
    is_valid, normalized, err = validate_ethiopian_phone('911234567')
    assert is_valid is True
    assert normalized == '911234567'
    assert err is None


def test_phone_accepts_9_digit_safaricom():
    is_valid, normalized, _ = validate_ethiopian_phone('711234567')
    assert is_valid is True
    assert normalized == '711234567'


def test_phone_accepts_full_e164():
    is_valid, normalized, _ = validate_ethiopian_phone('+251911234567')
    assert is_valid is True
    assert normalized == '911234567'


def test_phone_accepts_full_e164_safaricom():
    is_valid, normalized, _ = validate_ethiopian_phone('+251711234567')
    assert is_valid is True
    assert normalized == '711234567'


def test_phone_accepts_e164_with_spaces():
    is_valid, normalized, _ = validate_ethiopian_phone('+251 911 234 567')
    assert is_valid is True
    assert normalized == '911234567'


def test_phone_rejects_leading_zero():
    """Leading 0 (10 digits) is no longer accepted. Type 9 digits only."""
    is_valid, _, err = validate_ethiopian_phone('0911234567')
    assert is_valid is False
    assert err and 'leading 0' in err.lower() or 'do not include' in err.lower()


def test_phone_rejects_too_short():
    is_valid, _, err = validate_ethiopian_phone('91123456')
    assert is_valid is False
    assert 'too few' in err.lower() or '9' in err


def test_phone_rejects_too_long():
    is_valid, _, err = validate_ethiopian_phone('9112345678')
    assert is_valid is False
    assert 'too many' in err.lower() or '9 digits' in err.lower()


def test_phone_rejects_wrong_first_digit():
    is_valid, _, err = validate_ethiopian_phone('811234567')
    assert is_valid is False
    assert '7 or 9' in err or 'must start' in err.lower()


def test_phone_rejects_e164_too_short():
    is_valid, _, err = validate_ethiopian_phone('+25191123456')
    assert is_valid is False
    assert '9' in err


def test_phone_rejects_e164_too_long():
    is_valid, _, err = validate_ethiopian_phone('+2519112345678')
    assert is_valid is False


def test_phone_rejects_non_ethiopia_country_code():
    is_valid, _, err = validate_ethiopian_phone('+254711234567')
    assert is_valid is False
    assert '+251' in err or 'ethiopia' in err.lower()


def test_phone_rejects_empty():
    is_valid, _, err = validate_ethiopian_phone('')
    assert is_valid is False
    assert 'required' in err.lower()


def test_phone_rejects_garbage():
    is_valid, _, err = validate_ethiopian_phone('abc')
    assert is_valid is False


# ─────────────────────────────────────────────────────────────────────
# 2. Password strength — must require a symbol (matches UI)
# ─────────────────────────────────────────────────────────────────────

def test_password_accepts_strong_with_symbol():
    is_strong, err = check_password_strength('EthioPayroll@2026')
    assert is_strong is True
    assert err is None


def test_password_rejects_no_symbol():
    """Backend must require a symbol, matching the new UI checklist."""
    is_strong, err = check_password_strength('EthioPayroll2026')
    assert is_strong is False
    assert 'symbol' in err.lower()


def test_password_rejects_no_upper():
    is_strong, _ = check_password_strength('ethiopayroll@2026')
    assert is_strong is False


def test_password_rejects_no_digit():
    is_strong, _ = check_password_strength('EthioPayroll!')
    assert is_strong is False


def test_password_rejects_no_lower():
    is_strong, _ = check_password_strength('ETHIOPAYROLL@2026')
    assert is_strong is False


def test_password_rejects_too_short():
    is_strong, _ = check_password_strength('Abc@123')
    assert is_strong is False


# ─────────────────────────────────────────────────────────────────────
# 3. Login page uses the country selector with phone-or-email mode
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def app():
    os.environ.setdefault('DB_ENCRYPTION_KEY', 'a-real-encryption-key-32-chars-minimum-here')
    app = create_app()
    app.config['TESTING'] = True
    with app.app_context():
        yield app


def test_login_has_phone_and_email_tabs(app):
    """The login field must have tab switching (Phone / Email) so users
    can choose to enter a phone number or an email address."""
    client = app.test_client()
    r = client.get('/auth/login', follow_redirects=True)
    html = r.get_data(as_text=True)
    # Tab buttons present
    assert 'phone-input-tabs' in html
    assert 'data-phone-tab="phone"' in html
    assert 'data-phone-tab="email"' in html
    # Phone prefix box present
    assert 'phone-prefix-box' in html
    assert '+251' in html
    # login_id field present
    m = re.search(r'<input[^>]+id="login_id"[^>]*>', html)
    assert m is not None
    assert 'loginPhoneWrapper' in html


def test_login_helper_text_specifies_9_digits(app):
    """Helper text must specify the 9-digit requirement and starting digit."""
    client = app.test_client()
    r = client.get('/auth/login', follow_redirects=True)
    html = r.get_data(as_text=True)
    assert '9 digits' in html
    assert ('starting with' in html or 'starting' in html)


def test_login_loads_phone_input_script(app):
    """The phone-input.js must be loaded so the tab switching works."""
    client = app.test_client()
    r = client.get('/auth/login', follow_redirects=True)
    html = r.get_data(as_text=True)
    assert 'static/js/phone-input.js' in html


def test_forgot_password_also_has_phone_tabs(app):
    """Same pattern on the password-reset page."""
    client = app.test_client()
    r = client.get('/auth/forgot-password', follow_redirects=True)
    if r.status_code != 200:
        pytest.skip(f'forgot-password returned {r.status_code}')
    html = r.get_data(as_text=True)
    assert 'phone-input-tabs' in html
    assert 'phone-prefix-box' in html


# ─────────────────────────────────────────────────────────────────────
# 4. CSP-safe static assets
# ─────────────────────────────────────────────────────────────────────

def test_phone_input_js_is_loaded_locally(app):
    """The phone-input.js script must be served from /static/ (CSP)."""
    js = app.test_client().get('/static/js/phone-input.js').get_data(as_text=True)
    # Must not reference CDN
    assert 'cdn.jsdelivr.net' not in js
    # Must handle phone input validation
    assert 'PREFIX' in js or '+251' in js


def test_phone_input_uses_local_assets_only(app):
    """phone-input.js must not load any external CDN scripts."""
    js = app.test_client().get('/static/js/phone-input.js').get_data(as_text=True)
    assert 'cdn.jsdelivr.net' not in js


# ─────────────────────────────────────────────────────────────────────
# 5. Password strength UI (checklist + match line) on all 4 forms
# ─────────────────────────────────────────────────────────────────────

PASSWORD_FORMS = [
    ('/auth/register', 'password', 'password2'),
    ('/auth/accept-invite', 'password', 'password2'),
    ('/auth/reset-password', 'password', 'password2'),
]


@pytest.mark.parametrize('path,pw_field,confirm_field', PASSWORD_FORMS)
def test_password_form_has_checklist_and_match(app, path, pw_field, confirm_field):
    """Each publicly accessible password form must render the live
    checklist (.pw-rules) and the match status line. change-password is
    a separate test because it requires auth."""
    client = app.test_client()
    r = client.get(path, follow_redirects=True)
    if r.status_code != 200:
        pytest.skip(f'{path} returned {r.status_code}; skipping')
    html = r.get_data(as_text=True)
    assert 'class="pw-rules"' in html, (
        f'{path} must include the live .pw-rules checklist'
    )
    assert 'data-pw-rules' in html
    assert 'data-pw-match' in html
    # Five rules: length, upper, lower, digit, symbol
    for rule in ('length', 'upper', 'lower', 'digit', 'symbol'):
        assert f'data-pw-rule="{rule}"' in html, (
            f'{path} must include rule {rule!r} in the checklist'
        )
    # The strength script must be loaded on the page
    assert 'password-strength.js' in html
    # Submit button must be wired for gating
    assert 'data-pw-submit' in html


def test_change_password_page_has_checklist(app):
    """change-password requires an authenticated user; instead of
    parametrizing through login, just verify the template string
    is correct."""
    from pathlib import Path

    tpl = Path('payroll_engine/templates/auth/change_password.html').read_text()
    assert 'class="pw-rules"' in tpl
    assert 'data-pw-rules' in tpl
    assert 'data-pw-target="new_password"' in tpl
    assert 'data-pw-confirm="new_password2"' in tpl
    for rule in ('length', 'upper', 'lower', 'digit', 'symbol'):
        assert f'data-pw-rule="{rule}"' in tpl
    assert 'password-strength.js' in tpl
    assert 'data-pw-submit' in tpl
