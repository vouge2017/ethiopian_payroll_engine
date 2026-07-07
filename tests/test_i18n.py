"""
i18n tests — verifies Amharic string lookup and language switching.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine.i18n import get_string, get_all_strings, STRINGS


def test_amharic_lookup():
    assert get_string('dashboard', 'am') == 'ዳሽቦርድ'
    assert get_string('employees', 'am') == 'ሰራተኞች'
    assert get_string('net_pay', 'am') == 'ንፅ ደመወዝ'


def test_english_lookup():
    assert get_string('dashboard', 'en') == 'Dashboard'
    assert get_string('employees', 'en') == 'Employees'
    assert get_string('net_pay', 'en') == 'Net Pay'


def test_missing_key_returns_key():
    assert get_string('nonexistent', 'am') == 'nonexistent'
    assert get_string('nonexistent', 'en') == 'Nonexistent'


def test_all_strings_exist():
    all_am = get_all_strings('am')
    all_en = get_all_strings('en')
    assert len(all_am) == len(STRINGS)
    assert len(all_en) == len(STRINGS)
    assert len(all_am) > 25  # At least 25 strings


def test_critical_strings_exist():
    """These strings must exist for the core flow to work."""
    critical = [
        'dashboard', 'employees', 'payroll', 'reports',
        'basic_salary', 'net_pay', 'income_tax', 'employee_pension',
        'approve', 'download', 'save', 'cancel',
    ]
    for key in critical:
        assert key in STRINGS, f"Missing critical string: {key}"
        assert STRINGS[key] != '', f"Empty Amharic string: {key}"
