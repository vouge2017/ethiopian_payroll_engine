"""
Password policy tests.

Verifies the password strength requirements after the 2.1 hardening:
- Mixed case required (upper + lower)
- Digit required
- Common passwords rejected (expanded list)
- Dictionary word + year patterns rejected
- Keyboard patterns rejected
- Repeated characters rejected
- Sequential characters rejected
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CELERY_BROKER_URL'] = 'memory://'

from payroll_engine.password_policy import check_password_strength

# ---------------------------------------------------------------
# SHOULD PASS
# ---------------------------------------------------------------

def test_valid_passwords():
    """Strong passwords should be accepted."""
    valid = [
        'Tr0ub4dor&3',       # xkcd-style with special
        'MyP@ssw0rd!',       # mixed case + digit + special
        'Ethiopia#2026X',    # country + year but mixed case + special
        'C0mpl3x!Pass',      # all requirements met
        'SunRise4Ver',       # mixed case + digit
        'Xkcd9393!',         # random-ish
        'G3nu1n3ly$trong',   # long, complex
        'Qw3rTy!829',        # keyboard-ish but mixed + digit + special
    ]
    for pw in valid:
        is_strong, error = check_password_strength(pw)
        assert is_strong, f"'{pw}' should be accepted but got: {error}"


# ---------------------------------------------------------------
# SHOULD FAIL — Common passwords
# ---------------------------------------------------------------

def test_common_passwords_rejected():
    """Common passwords must be rejected."""
    common = [
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'admin', 'admin123', 'letmein', 'welcome', 'monkey',
        'ethiopia', 'addis', 'tigist', 'dawit', 'payroll',
        'Password1', 'password!', 'Password123',  # common + suffix
    ]
    for pw in common:
        is_strong, error = check_password_strength(pw)
        assert not is_strong, f"'{pw}' should be rejected but was accepted"


# ---------------------------------------------------------------
# SHOULD FAIL — Mixed case requirement
# ---------------------------------------------------------------

def test_requires_uppercase():
    """Password without uppercase must be rejected."""
    is_strong, error = check_password_strength('alllower1!')
    assert not is_strong
    assert 'uppercase' in error.lower()


def test_requires_lowercase():
    """Password without lowercase must be rejected."""
    is_strong, error = check_password_strength('ALLUPPER1!')
    assert not is_strong
    assert 'lowercase' in error.lower()


def test_requires_digit():
    """Password without digit must be rejected."""
    is_strong, error = check_password_strength('NoDigits!')
    assert not is_strong
    assert 'digit' in error.lower()


# ---------------------------------------------------------------
# SHOULD FAIL — Patterns from checkpoint review
# ---------------------------------------------------------------

def test_dict_word_plus_year_rejected():
    """Dictionary word + year patterns must be rejected."""
    patterns = [
        'ethiopia2025', 'addis2026', 'tigist123', 'dawit99',
        'habesha2025', 'payroll2026', 'salary1234',
        'password2025', 'admin2026', 'welcome123',
    ]
    for pw in patterns:
        is_strong, error = check_password_strength(pw)
        assert not is_strong, f"'{pw}' should be rejected but got: {error}"


def test_common_plus_suffix_rejected():
    """Common password + special char suffix must be rejected."""
    patterns = ['password!', 'admin@', 'welcome#', 'ethiopia$', 'tigist!']
    for pw in patterns:
        is_strong, error = check_password_strength(pw)
        assert not is_strong, f"'{pw}' should be rejected but got: {error}"


def test_repeated_chars_rejected():
    """Repeated character runs must be rejected."""
    patterns = ['aaa111BBB', 'Aaa111!!!', 'abcdddABC1']
    for pw in patterns:
        is_strong, error = check_password_strength(pw)
        assert not is_strong, f"'{pw}' should be rejected but got: {error}"


def test_keyboard_patterns_rejected():
    """Keyboard walk patterns must be rejected."""
    patterns = ['Qwerty123!', 'Asdf9876!', '1Qaz2Wsx!', 'Abcdef1!']
    for pw in patterns:
        is_strong, error = check_password_strength(pw)
        assert not is_strong, f"'{pw}' should be rejected but got: {error}"


def test_sequential_chars_rejected():
    """Sequential character runs must be rejected."""
    patterns = ['Abcd1234!', 'Dcba4321!', 'Xyz9876!A']
    for pw in patterns:
        is_strong, error = check_password_strength(pw)
        assert not is_strong, f"'{pw}' should be rejected but got: {error}"


# ---------------------------------------------------------------
# SHOULD FAIL — Edge cases
# ---------------------------------------------------------------

def test_empty_password():
    is_strong, error = check_password_strength('')
    assert not is_strong
    assert 'required' in error.lower()


def test_too_short():
    is_strong, error = check_password_strength('Ab1!')
    assert not is_strong
    assert '8 characters' in error


def test_too_long():
    is_strong, error = check_password_strength('A' * 129 + 'b1!')
    assert not is_strong
    assert 'too long' in error.lower()


def test_all_same_char():
    is_strong, error = check_password_strength('aaaaaaaa')
    assert not is_strong


def test_all_symbols():
    is_strong, error = check_password_strength('!@#$%^&*')
    assert not is_strong
    assert 'letter' in error.lower() or 'number' in error.lower()
