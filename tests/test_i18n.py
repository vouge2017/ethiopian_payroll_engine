"""
i18n tests — verifies Amharic string lookup and language switching.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine.i18n import get_string, get_all_strings, STRINGS
from payroll_engine.i18n_om import STRINGS_OM


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


# --- Afaan Oromoo Tests ---


def test_oromo_lookup():
    """Afaan Oromoo translations return correct values."""
    assert get_string('dashboard', 'om') == 'Gabatee'
    assert get_string('employees', 'om') == 'Hojjetaanota'
    assert get_string('payroll', 'om') == 'Kaffaltii'
    assert get_string('net_pay', 'om') == 'Kaffaltii xiqqaa'
    assert get_string('welcome', 'om') == 'Baga nagaan dhuftan'


def test_oromo_all_keys_have_translations():
    """Every English key should have an Afaan Oromoo translation."""
    all_en = get_all_strings('en')
    all_om = get_all_strings('om')
    missing = set(all_en.keys()) - set(all_om.keys())
    assert len(missing) == 0, f"Missing Afaan Oromoo translations: {missing}"


def test_oromo_no_empty_values():
    """No Afaan Oromoo translation should be empty."""
    for key, value in STRINGS_OM.items():
        assert value != '', f"Empty Afaan Oromoo string: {key}"


def test_oromo_has_minimum_strings():
    """At least 50 Afaan Oromoo strings for usable coverage."""
    assert len(STRINGS_OM) >= 50, f"Only {len(STRINGS_OM)} Afaan Oromoo strings (need 50+)"


def test_oromo_critical_strings():
    """Critical payroll flow strings must exist in Afaan Oromoo."""
    critical = [
        'dashboard', 'employees', 'payroll', 'reports',
        'basic_salary', 'net_pay', 'income_tax', 'employee_pension',
        'approve', 'download', 'save', 'cancel', 'welcome',
        'erca_deadline', 'pension_deadline', 'payslip',
    ]
    for key in critical:
        assert key in STRINGS_OM, f"Missing critical Afaan Oromoo string: {key}"
        assert STRINGS_OM[key] != '', f"Empty critical Afaan Oromoo string: {key}"


def test_oromo_fallback_to_key():
    """Unknown keys should return the key itself."""
    assert get_string('nonexistent_key_xyz', 'om') == 'nonexistent_key_xyz'
